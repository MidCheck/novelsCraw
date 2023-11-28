from prettytable import PrettyTable
from pathlib import Path
import argparse
import asyncio
import importlib
import sys
import os

from ._base import NCType, NovelCrawBase

_novel_craws: list[NovelCrawBase] = []
for file in Path(__file__).parent.iterdir():
    if file.name in ('__init__.py', '_base.py', '__main__.py') or \
            not file.name.endswith('.py'):
        continue
    module = importlib.import_module(
        '.%s' % file.name[:-3], '%s' % file.parent.name
    )
    for object in module.__dict__.values():
        if type(object) != type or \
                not issubclass(object, NovelCrawBase) or \
                not hasattr(object, 'sitename') or object.sitename is None or \
                not hasattr(object, 'siteurl') or object.siteurl is None:
            continue
        if object in _novel_craws:
            raise RuntimeError(f"duplicate novel craw {object.sitename}: {object.siteurl}")
        _novel_craws.append(object)
        break
    del sys.modules[module.__name__]
    del module


async def search(args) -> tuple[NovelCrawBase, str, str]:
    store_dir = Path(args.directory)
    store_dir.mkdir(exist_ok=True)

    craws: list[NovelCrawBase] = [craw(store_dir, args.type, args.nums, args.timeout) for craw in _novel_craws]
    tasks: list[asyncio.Task] = []
    async with asyncio.TaskGroup() as tg:
        for craw in craws:
            tasks.append(tg.create_task(craw.search(args.name), name=craw.sitename))
    
    craws_indexs = []
    data_rows = []
    for task in tasks:
        if args.top == 0:
            result = task.result()
        else:
            result = task.result()[:args.top]
        start_idx = len(data_rows)
        end_idx = len(result)
        craws_indexs.append((start_idx, start_idx + end_idx))
        data_rows += result
    data_rows_size = len(data_rows)

    table = PrettyTable(['序号', '小说名称', '作者', '小说网址', '更新日期'])
    table.align['小说网址'] = 'l'
    # table.align['最新章节地址'] = 'l'
    for i in range(data_rows_size):
        noval_name, author, url, update_date = data_rows[i]
        table.add_row([i+1, noval_name, author, url, update_date])
    print(table)
    while True:
        choice = input(f"请选择要下载的小说序号(1-{data_rows_size}): ")
        if not choice:
            print("[!] 没有选择想要下载的小说,退出工具")
            return None
        if not choice.isdigit() or int(choice) < 1 or int(choice) > data_rows_size:
            print(f"[-] 没有该序号'{choice}'的小说,请重新选择...")
            continue
        idx = int(choice)-1
        for i in range(len(craws_indexs)):
            if idx >= craws_indexs[i][0] and idx < craws_indexs[i][1]:
                craw = craws[i]
                for j in range(len(craws_indexs)):
                    if j != i:
                        del craws[j] # release
                return craw, data_rows[idx][0], data_rows[idx][2]
        return None, None, None

async def main():
    parser = argparse.ArgumentParser(description="novelScraw: 小说爬取工具")
    parser.add_argument("name", metavar="novel_name", help="小说名称")
    parser.add_argument(
        "-d", "--directory", 
        default=os.getcwd(), metavar="download_dir", 
        help="小说下载后存储位置,默认为当前目录"
    )
    parser.add_argument(
        "-t", "--type", 
        default=NCType.TXT.name, metavar="store_type",
        choices=[t.name for t in list(NCType)],
        help=f"小说下载后存储类型: {[t.name for t in list(NCType)]}, 默认为TXT格式: "
    )
    parser.add_argument(
        "-n", "--nums", 
        default=20, metavar="craw_worker_nums", type=int, 
        help="并行爬取数量,默认为20个协程"
    )
    parser.add_argument(
        "--timeout", 
        default=60, metavar="timeout", type=int, 
        help="下载文章时的超时时间,单个链接超过该时间认为下载失败,默认超时60s"
    )
    parser.add_argument(
        "--top",
        default=0, metavar="toplinks", type=int,
        help="每个网站只显示前top个链接,默认为0,显示全部的链接"
    )
    args = parser.parse_args()
    for t in list(NCType):
        if args.type == t.name:
            args.type = t
            break
    
    craw, name, url = await search(args)
    await craw.craw(name, url)


if __name__ == '__main__':
    asyncio.run(main())
