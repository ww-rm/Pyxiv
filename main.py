from argparse import ArgumentParser

from pyxiv import PyxivBrowser, PyxivConfig

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--config", type=str, default="config.json", help="a json file which stores pyxiv configs")
    args = parser.parse_args()

    config = PyxivConfig().load(args.config)
    pyxiv = PyxivBrowser(config)

    pyxiv.download_all()
    # pyxiv.download_illusts()
    # pyxiv.download_users()
