from requests_html import AsyncHTMLSession
from prettytable import PrettyTable
from pathlib import Path
import argparse
import asyncio
import re

root_url = "https://www.ibiquges.org"
rootdir = Path(__file__).parent

async def get_href_links(asession: AsyncHTMLSession, queue: asyncio.Queue, href: str):
    try:
        resp = await asession.get(root_url + href)
    except Exception as e:
        print("[-] 获取首页目录失败:", str(e))
    else:
        i = 0
        if matched := re.findall('''<dd><a href=\\'(.*?)\\' >(.*?)</a></dd>''', resp.html.html):
            for href, title in matched:
                queue.put_nowait((i, href, title))
                i += 1
        print(f"[+] 共有{i}条链接待下载...")
        return i

async def get_content(asession: AsyncHTMLSession, queue: asyncio.Queue, txt: dict):
    while True:
        try:
            i, href, title = await queue.get()
            resp = await asession.get(root_url + href)
            if resp.status_code != 200:
                queue.task_done()
                raise Exception(f"http status code: {resp.status_code}")
            div = resp.html.find('div#content', first=True)
            if matched := re.findall(r'最新网址.*?\s(.*?)\n\n\n', div.text, re.DOTALL):
                # # 为段落开头添加两个空格
                # content = re.sub(r"^(.*)$", r"  \1", matched[0], flags=re.DOTALL)
                # txt[i] = f"    {title}\n{content}\n\n\n"
                txt[i] = f"----\n{title}\n----\n{matched[0]}\n\n\n"
            queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[-] {title} '{href}': {str(e)}")
            await queue.put((i, href, title))


async def download_noval_txt(asession: AsyncHTMLSession, noval_name: str, noval_href: str, works: int=20):
    queue = asyncio.Queue()
    txt = {}
    tasks = [ asyncio.create_task(get_content(asession, queue, txt)) for _ in range(works)]
    try:
        total = await get_href_links(asession, queue, noval_href)
        while True:
            txt_size = len(txt)
            print(f'\b\r[.] 下载"{noval_name}"进度: {txt_size}/{total}', end='')
            if txt_size >= total:
                print()
                break
            await asyncio.sleep(1)
        print(f"[+] 下载 {noval_name} 完成!")
        for task in tasks:
            task.cancel()
    except Exception as e:
        print('[-] 等待下载任务出错:', str(e))
    
    with open(rootdir.joinpath(noval_name + ".txt"), 'w', encoding='utf-8') as f:
        for i in sorted(txt):
            f.write(txt[i])
    print(f"[+] 存储完成,保存路径: {noval_name}.txt")


async def search_noval_href(asession: AsyncHTMLSession, noval_name: str) -> str:
    pattern = re.compile(r'''<tr>\s*<td class="even"><a href="(.*?)" target="_blank">(.*?)</a></td>\s*<td class="odd"><a href="(.*?)" target="_blank">(.*?)</a>\s*</td>\s*<td class="even">(.*?)</td>\s*<td class="odd" align="center">(\S*)\s*</td>\s*</tr>''', re.DOTALL)
    table = PrettyTable(['序号', '小说名称', '作者', '小说网址', '更新日期']) # '最新章节', '最新章节地址'
    table.align['小说网址'] = 'l'
    # table.align['最新章节地址'] = 'l'
    try:
        resp = await asession.post(root_url + "/modules/article/waps.php", data={'searchkey': noval_name})
        if matched := pattern.findall(resp.html.html):
            for i in range(len(matched)):
                noval_url, noval, last_href, last_title, author, update_date = matched[i]
                table.add_row([i+1, noval, author, noval_url, update_date]) # , last_title, last_href
            print(table)
            while True:
                choice = input(f"请选择要下载的小说序号(1-{len(matched)}): ")
                if not choice:
                    print("[!] 没有选择想要下载的小说,退出工具")
                    return None
                if not choice.isdigit() or int(choice) < 1 or int(choice) > len(matched):
                    print(f"[-] 没有该序号'{choice}'的小说,请重新选择...")
                    continue
                idx = int(choice)-1
                url: str
                name, url = matched[idx][1], matched[idx][0]
                if url.startswith(root_url):
                    return name, url.replace(root_url, '')
                return name, url
    except Exception as e:
        print("[-] 搜索小说出错:", str(e))
        return None

async def main(noval_name: str, noval_href: str, works: int):
    asession = AsyncHTMLSession()
    if not noval_href:
        # 搜索小说
        result = await search_noval_href(asession, noval_name)
        if result is None:
            return
        noval_name, noval_href = result

    await download_noval_txt(asession, noval_name, noval_href, works)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="novelScraw: 小说爬取工具")
    parser.add_argument("name", metavar="novel_name", help="小说名称")
    parser.add_argument("--href", metavar="href_path", help="小说首页URL中的路径部分,未指定时使用小说名称进行搜索")
    parser.add_argument("-n", "--nums", default=20, metavar="craw_worker_nums", type=int, help="并行爬取数量,默认为20个协程")
    args = parser.parse_args()

    asyncio.run(main(args.name, args.href, args.nums))
