from argparse import ArgumentParser

from pyxiv import PyxivBrowser, PyxivConfig, PyxivDownloader

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--config", type=str, default="config.json", help="a json file which stores pyxiv configs")
    args = parser.parse_args()

    config = PyxivConfig().load(args.config)
    browser = PyxivBrowser(config.proxies, config.cookies)


    browser.get_page("https://i.pximg.net/img-original/img/2021/03/16/03/20/03/88483729_p0.png")
    # downloader.download_illusts()
    # downloader.download_users()
