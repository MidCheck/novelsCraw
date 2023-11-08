# novelsCraw
novelsCraw是一个小说爬取工具，可以将搜索到的小说下载到本地阅读，适用于不想被网站广告打扰和在线阅读无网络情况

## 使用方法
```
$ python3 novel_scraw.py -h
usage: novel_scraw.py [-h] [--href href_path] [-n craw_worker_nums] novel_name

novelScraw: 小说爬取工具

positional arguments:
  novel_name            小说名称

options:
  -h, --help            show this help message and exit
  --href href_path      小说首页URL中的路径部分,未指定时使用小说名称进行搜索
  -n craw_worker_nums, --nums craw_worker_nums
                        并行爬取数量,默认为20个协程
```

## 支持的小说网站
`*感谢以下网站提供的免费小说资源*`

| 时间 | 网站名称 | 网站地址 |
|:----:|:-------:|:---------|
| 2023-11-09 | 香书小说 | https://www.ibiquges.org/ |


## 功能
- [x] 搜索小说
- [x] 将小说下载为TXT
- [ ] 将小说下载为支持本地打开的html
