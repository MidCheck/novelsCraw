from ._base import NovelCrawBase, HTML
import urllib.parse
import re

class IBiqugesCraw(NovelCrawBase):
    siteurl: str = "https://www.ibiquges.org"
    sitename: str = "香书小说" # 2023-11-09

    search_pattern = re.compile(r'''<tr>\s*<td class="even"><a href="(.*?)" target="_blank">(.*?)</a></td>\s*<td class="odd"><a href="(.*?)" target="_blank">(.*?)</a>\s*</td>\s*<td class="even">(.*?)</td>\s*<td class="odd" align="center">(\S*)\s*</td>\s*</tr>''', re.DOTALL)
    dirlinks_pattern = re.compile('''<dd><a href=\\'(.*?)\\' >(.*?)</a></dd>''')
    content_pattern = re.compile(r'最新网址.*?\s(.*?)\n\n\n', re.DOTALL)

    async def search(self, searchkey: str) -> [tuple[str, str, str, str]]: # novelname, author, url, update_date
        results = []
        url = urllib.parse.urljoin(self.siteurl, "/modules/article/waps.php")
        try:
            resp = await self.asession.post(url, data={'searchkey': searchkey})
            if matched := self.search_pattern.findall(resp.html.html):
                for i in range(len(matched)):
                    noval_url, noval, last_href, last_title, author, update_date = matched[i]
                    results.append((noval, author, noval_url, update_date))
            else:
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
        div = html.find('div#content', first=True)
        if matched := self.content_pattern.findall(div.text):
            return matched[0]
        return None
