from config import PyxivConfig
from pyxiv import Pyxiv
from argparse import ArgumentParser

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--config", type=str, default="config.json", help="a json file which stores pyxiv configs")
    args = parser.parse_args()

    config = PyxivConfig().load(args.config)
    pyxiv = Pyxiv(config)

    pyxiv.download_all()
