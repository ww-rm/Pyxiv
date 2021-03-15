from argparse import ArgumentParser

from pyxiv import PyxivBrowser, PyxivConfig

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--config", type=str, default="config.json", help="a json file which stores pyxiv configs")
    args = parser.parse_args()

    config = PyxivConfig().load(args.config)
    browser = PyxivBrowser(config)

    browser.download_all()
    # browser.download_illusts()
    # browser.download_users()
