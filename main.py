from argparse import ArgumentParser

from pyxiv import PyxivSpider, PyxivConfig

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--config", type=str, default="config.json", help="a json file which stores pyxiv configs")
    args = parser.parse_args()

    spider = PyxivSpider(args.config)

    # use methods with spider to download pixiv illusts
    print(help(spider))