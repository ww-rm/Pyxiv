import json
import sys


class PyxivConfig:
    setter_warning = "Warning: Failed to set {value}"

    def __init__(self):
        self.__proxies = {"http": "http://127.0.0.1:10809", "https": "http://127.0.0.1:10809"}
        self.__illusts = tuple()
        self.__users = tuple()
        self.__save_path = "."

    @property
    def proxies(self):
        return self.__proxies.copy()

    @proxies.setter
    def proxies(self, value):
        try:
            self.__proxies = {"http": str(value["http"]), "https": str(value["https"])}
        except (TypeError, KeyError):
            print(PyxivConfig.setter_warning.format(value="proxies"), file=sys.stderr)

    @property
    def illusts(self):
        return self.__illusts

    @illusts.setter
    def illusts(self, value):
        try:
            self.__illusts = tuple(map(int, value))
        except TypeError:
            print(PyxivConfig.setter_warning.format(value="illusts"), file=sys.stderr)

    @property
    def users(self):
        return self.__users

    @users.setter
    def users(self, value):
        try:
            self.__users = tuple(map(int, value))
        except TypeError:
            print(PyxivConfig.setter_warning.format(value="users"), file=sys.stderr)

    @property
    def save_path(self):
        return self.__save_path

    @save_path.setter
    def save_path(self, value):
        try:
            self.__save_path = str(value)
        except TypeError:
            print(PyxivConfig.setter_warning.format(value="save_path"), file=sys.stderr)

    def load(self, path: str):
        with open(path, "r", encoding="utf8", errors="ignore") as f:
            config = json.load(f)
        self.proxies = config.get("proxies")
        self.illusts = config.get("illusts")
        self.users = config.get("users")
        self.save_path = config.get("save_path")
        return self

    def save(self, path: str):
        config = {
            "proxies": self.proxies,
            "illusts": self.illusts,
            "users": self.users,
            "save_path": self.save_path
        }
        with open(path, "w", encoding="utf8", errors="ignore") as f:
            json.dump(config, f)
        return self