from ._base import NovelCrawBase, HTML
import urllib.parse
import re
import json

class JunjhCraw(NovelCrawBase):
    siteurl: str = "https://www.junjh.com/"
    sitename: str = "笔趣阁全本小说网(读小说)" # 2023-11-29

    headers = {
        'accept': 'application/json',
        'user-agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Mobile Safari/537.36 uacq',
    }
    dirlinks_pattern = re.compile(r'''<li>\s*<a href="(.*)" title="(.*)">.*</a>\s*</li>''')

    async def search(self, searchkey: str) -> [tuple[str, str, str, str]]: # novelname, author, url, update_date
        results = []
        url = urllib.parse.urljoin(self.siteurl, "/api/search")
        url += '?' + urllib.parse.urlencode({'q': searchkey})
        try:
            resp = await self.asession.get(url, headers=self.headers)
            if resp.status_code != 200:
                raise Exception(f"http状态码: {resp.status_code}")
            result = json.loads(resp.html.html)
            if 'code' not in result or result['code'] != 0 or \
                    'data' not in result or 'search' not in result['data']:
                raise Exception(f"错误的响应格式: {result}")
            for obj in result['data']['search']:
                dirurl = urllib.parse.urljoin(self.siteurl, obj['book_list_url'])
                results.append((obj['book_name'], obj['author'], dirurl, obj['uptime']))
            if not results:
                print(f"[-] 小说网站'{self.sitename}'没有搜索到内容")
        except Exception as e:
            print(f"[-] 小说网站'{self.sitename}'搜索小说出错:", str(e))
        finally:
            return results
        
    async def get_links(self, html: HTML) -> [tuple[str, str]]: # title, href
        if matched := self.dirlinks_pattern.findall(html.html):
            return [(title, href) for href, title in matched]
        return []
    
    async def get_content(self, html: HTML) -> str:
        if div := html.find('div#htmlContent', first=True):
            if p := div.find('p', first=True):
                return p.text
        return None
