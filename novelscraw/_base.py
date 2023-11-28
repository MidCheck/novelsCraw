from requests_html import AsyncHTMLSession, HTML
from pathlib import Path
from enum import Enum
import urllib.parse
import asyncio
import time


class NCType(Enum):
    TXT  = 1
    HTML = 2
    DB   = 3


class NovelCrawBase:
    sitename: str = None
    siteurl: str = None

    def __init__(self, storedir: Path, type: NCType=NCType.TXT, works: int=20, timeout: int=60):
        self.rootdir = storedir
        self.download_type = type
        self.works = works
        self.timeout = timeout
        self.novelname = None
        self.asession: AsyncHTMLSession = AsyncHTMLSession()
        self.queue: asyncio.Queue = None
        self.db: dict = None

    async def download_content_worker(self):
        while True:
            try:
                idx, href, title = await self.queue.get()
                if idx in self.db:
                    raise Exception(f"重复的内容: {idx} -> '{self.db[idx]}'")
                url = urllib.parse.urljoin(self.siteurl, href)
                resp = await self.asession.get(url)
                if resp.status_code != 200:
                    raise Exception(f"http status code: {resp.status_code}")
                if content := await self.get_content(resp.html):
                    self.db[idx] = (title, content)
                else:
                    raise Exception(f"没有获取到文本内容: '{title}' -> '{url}'")
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[-] 下载文章出错: {str(e)}")
                self.queue.task_done()
            else:
                self.queue.task_done()
                

    async def get_content(self, html: HTML) -> str:
        raise NotImplementedError
    
    async def get_links(self, html: HTML) -> [tuple[str, str]]: # title, href
        raise NotImplementedError

    async def search(self, searchkey: str) -> [tuple[str, str, str, str]]: # novelname, author, url, update_date
        raise NotImplementedError

    def _store_txt(self):
        path = self.rootdir.joinpath(f'{self.novelname}.txt')
        with open(path, 'w', encoding='utf-8') as f:
            for i in sorted(self.db):
                title, txt = self.db[i]
                content = f"----\n{title}\n----\n{txt}\n\n\n"
                f.write(content)
        return str(path)
    
    def _store_html(self):
        def gen_html(i, prev, next):
            title, txt = self.db[i]
            txt: str = txt.replace(' ', '&nbsp')
            txt = txt.replace('\n', '<br/>')
            footer = f'''</br><a href="/{prev}.html">上一章</a>&nbsp&nbsp<a href="/{next}.html">下一章</a>'''
            return f'''<!DOCTYPE html><html><head><title>{title}</title></head><body><h1>{title}</h1><p>{txt}</p>{footer}</body></html>'''
        postfix = time.strftime("%Y%m%d%H%M%S", time.localtime(time.time()))
        path = self.rootdir.joinpath(f'{self.novelname}_' + postfix)
        path.mkdir(exist_ok=True)
        
        keys = sorted(self.db)
        # first key
        with open(path.joinpath(f'{keys[0]}.html'), 'w') as f:
            f.write(gen_html(0, 0, 1))
        for i in keys[1:-1]:
            with open(path.joinpath(f'{keys[i]}.html'), 'w') as f:
                f.write(gen_html(i, i-1, i+1))
        with open(path.joinpath(f'{keys[-1]}.html'), 'w') as f:
            idx = len(keys) - 1
            f.write(gen_html(idx, idx-1, idx))
        return str(path)

    def _store_db(self):
        pass

    async def craw(self, name: str, directory_url: str):
        self.queue = asyncio.Queue()
        self.db = dict()

        self.novelname = name
        print(f'[.] 从网站"{self.sitename}"下载小说"{self.novelname}"...')
        try:
            resp = await self.asession.get(directory_url)
            if resp.status_code != 200:
                raise Exception(f"http status code: {resp.status_code}")
            links = await self.get_links(resp.html)
            if not links:
                raise Exception(f"没有解析到小说'{self.novelname}'目录")
        except Exception as e:
            print("[-] 获取小说目录网页失败:", str(e))
            return
        else:
            total_links = len(links)
            print(f"[+] 共有{total_links}条链接待下载...")
        
        tasks = [asyncio.create_task(self.download_content_worker()) for _ in range(self.works)]
        for i in range(total_links):
            await self.queue.put((i, links[i][1], links[i][0])) # idx, href, title
        
        # await workers finish
        last_finished = len(self.db)
        last_time = int(time.time())
        while True:
            finished = len(self.db)
            now = int(time.time())
            if finished == last_finished and now - last_time >= self.timeout:
                print(f'\n[-] 下载"{self.novelname}"超时,结束下载')
                break
            last_time = now
            last_finished = finished

            print(f'\b\r[.] 下载"{self.novelname}"进度: {finished}/{total_links}', end='')
            if finished >= total_links:
                print(f'\n[+] 下载"{self.novelname}"完成!')
                break
            await asyncio.sleep(1)
        
        # stop all workers
        for task in tasks:
            task.cancel()
        
        # check timeout
        if len(self.db) != total_links:
            cont = input(f'[!] "{self.novelname}"下载不完整,是否保存(Y/n)?')
            if cont == 'n' or cont == 'N':
                return
        
        print(f'[.] 保存小说"{self.novelname}" {len(self.db)}/{total_links}章 ...')
        # store
        match self.download_type:
            case NCType.TXT:
                path = self._store_txt()
            case NCType.HTML:
                path = self._store_html()
            case NCType.DB:
                path = self._store_db()
        print(f"[+] 存储完成,保存路径: {path}")
