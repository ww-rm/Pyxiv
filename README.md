# Pyxiv

A small tool to download images on pixiv.

## How to use

- Basic Class ```PyxivBroswer``` and ```PyxivDatabase``` are defined in [pyxivbase.py](https://github.com/ww-rm/Pyxiv/blob/main/pyxivbase.py)
- Main class ```PyxivSpider``` is defined in [pyxiv.py](https://github.com/ww-rm/Pyxiv/blob/main/pyxiv.py)
- There is also a sample [config.json](https://github.com/ww-rm/Pyxiv/blob/main/config.json) file to show config format
- To use it, see docs written in Class ```PyxivSpider``` and short sample codes in [main.py](https://github.com/ww-rm/Pyxiv/blob/main/main.py)

## Main Features

- Store metadata of illusts in a database
- Can automatic crawl illusts information by BFS, using recommendation mechanism of pixiv
- Before download an illust, first look up metadata in database to save time; if not found, will store to database
- Support to search popular illusts in local database by crawling with sufficient metadata

## **Important**

**LIMIT YOUR SPEED AND NOT PUT HEAVY PRESSURE TO PIXIV'S SERVER!!!**

---

*If you think this project is helpful to you, plz star it and let more people see it. :)*
