import json
import os
import random
import sys
from pathlib import PurePath
from time import sleep

import requests


class PyxivConfig:
    setter_warning = "Warning: Failed to set {value}"

    def __init__(self):
        self.__proxies = {}
        self.__illusts = tuple()
        self.__users = tuple()
        self.__save_path = "."
        self.__R18 = False
        self.__cookies = {}

    def __setter_warn(self, value):
        print(PyxivConfig.setter_warning.format(value=value), file=sys.stderr)

    @property
    def proxies(self):
        return self.__proxies.copy()

    @proxies.setter
    def proxies(self, value):
        try:
            self.__proxies = {"http": str(value["http"]), "https": str(value["https"])}
        except (TypeError, KeyError):
            self.__setter_warn("proxies")

    @property
    def illusts(self):
        return self.__illusts

    @illusts.setter
    def illusts(self, value):
        try:
            self.__illusts = tuple(map(int, value))
        except TypeError:
            self.__setter_warn("illusts")

    @property
    def users(self):
        return self.__users

    @users.setter
    def users(self, value):
        try:
            self.__users = tuple(map(int, value))
        except TypeError:
            self.__setter_warn("users")

    @property
    def save_path(self):
        return self.__save_path

    @save_path.setter
    def save_path(self, value):
        try:
            self.__save_path = str(value)
        except TypeError:
            self.__setter_warn("save_path")

    @property
    def R18(self):
        return self.__R18

    @R18.setter
    def R18(self, value):
        try:
            self.__R18 = bool(value)
        except TypeError:
            self.__setter_warn("R18")

    @property
    def cookies(self):
        return self.__cookies.copy()

    @cookies.setter
    def cookies(self, value):
        try:
            self.__cookies = {
                "PHPSESSID": str(value["PHPSESSID"]),
                "device_token": str(value["device_token"]),
                "privacy_policy_agreement": str(value["privacy_policy_agreement"])
            }
        except (TypeError, KeyError):
            raise
            self.__setter_warn("cookies")

    def load(self, path: str):
        with open(path, "r", encoding="utf8", errors="ignore") as f:
            config = json.load(f)
        self.proxies = config.get("proxies")
        self.illusts = config.get("illusts")
        self.users = config.get("users")
        self.save_path = config.get("save_path")
        self.R18 = config.get("R18")
        self.cookies = config.get("cookies")
        return self

    def save(self, path: str):
        config = {
            "proxies": self.proxies,
            "illusts": self.illusts,
            "users": self.users,
            "save_path": self.save_path,
            "R18": self.R18,
            "cookies": self.cookies
        }
        with open(path, "w", encoding="utf8", errors="ignore") as f:
            json.dump(config, f)
        return self


class PyxivBrowser:
    # lang=zh
    # 获取所有illust的id
    url_host = "https://www.pixiv.net"
    url_user = "https://www.pixiv.net/ajax/user/{user_id}"  # user simple info
    url_user_all = "https://www.pixiv.net/ajax/user/{user_id}/profile/all"  # user all illusts and details # 9930155
    url_user_top = "https://www.pixiv.net/ajax/user/{user_id}/profile/top"
    url_user_illusts = "https://www.pixiv.net/ajax/user/{user_id}/illusts?ids[]=84502979"

    url_illust = "https://www.pixiv.net/ajax/illust/{illust_id}"  # illust details # 70850475
    url_illust_pages = "https://www.pixiv.net/ajax/illust/{illust_id}/pages"  # illust pages

    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36",
        "referer": url_host
    }

    def __init__(self, config: PyxivConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers = PyxivBrowser.headers
        self.session.proxies = config.proxies
        self.session.cookies.update(config.cookies)
        self.__random_max_sleep = 5
        # print(self.session.cookies)

    def __del__(self):
        self.session.close()

    def _randsleep(self):
        # random sleep [0.1, max) seconds
        sleep(0.1+random.random()*(self.__random_max_sleep-0.1))

    def _get_illust(self, illust_id):
        json_ = self.session.get(PyxivBrowser.url_illust.format(illust_id=illust_id)).json()
        self._randsleep()
        if json_.get("error") is True:
            print("Error: _get_illust illust_id: {}".format(illust_id), file=sys.stderr)
            return {}
        else:
            return json_.get("body")

    def _get_illust_pages(self, illust_id):
        json_ = self.session.get(PyxivBrowser.url_illust_pages.format(illust_id=illust_id)).json()
        self._randsleep()

        if json_.get("error") is True:
            print("Error: _get_illust_pages illust_id: {}".format(illust_id), file=sys.stderr)
            return {}
        else:
            return json_.get("body")

    def _get_user(self, user_id):
        json_ = self.session.get(PyxivBrowser.url_user.format(user_id=user_id)).json()
        self._randsleep()

        if json_.get("error") is True:
            print("Error: _get_user user_id: {}".format(user_id), file=sys.stderr)
            return {}
        else:
            return json_.get("body")

    def _get_user_all(self, user_id):
        json_ = self.session.get(PyxivBrowser.url_user_all.format(user_id=user_id)).json()
        self._randsleep()

        if json_.get("error") is True:
            print("Error: _get_user_all user_id: {}".format(user_id), file=sys.stderr)
            return {}
        else:
            return json_.get("body")

    def _get_user_top(self, user_id):
        json_ = self.session.get(PyxivBrowser.url_user_top.format(user_id=user_id)).json()
        self._randsleep()

        if json_.get("error") is True:
            print("Error: _get_user_all user_id: {}".format(user_id), file=sys.stderr)
            return {}
        else:
            return json_.get("body")

    def save_illust(self, illust_id, save_path):
        """save illust"""
        illust_pages = self._get_illust_pages(illust_id)
        all_pages = {
            page.get("urls").get("original").split("/")[-1]: page.get("urls").get("original")
            for page in illust_pages
        }
        exist_pages = os.listdir(save_path)

        pages_need_to_save = set(all_pages.keys()) - set(exist_pages)
        for page_id in pages_need_to_save:
            page_path = PurePath(save_path, page_id)
            response = self.session.get(all_pages[page_id])
            self._randsleep()
            print("\tsaving page: {}".format(page_path))
            with open(page_path, "wb") as f:
                f.write(response.content)
        return True

    def save_illusts(self, illust_ids, save_path):
        for illust_id in illust_ids:
            illust = self._get_illust(illust_id)
            print("saving illust: {}".format(illust_id))
            illust_save_path = save_path
            if self.config.R18 and "R-18" in [tag.get("tag") for tag in illust.get("tags").get("tags")]:
                illust_save_path = PurePath(illust_save_path, "R-18")
            os.makedirs(illust_save_path, exist_ok=True)
            self.save_illust(illust_id, illust_save_path)
        return True

    def save_users(self, user_ids, save_path):
        for user_id in user_ids:
            user = self._get_user(user_id)
            user_all = self._get_user_all(user_id)
            user_name = user.get("name")
            all_illusts = list(user_all.get("illusts").keys())
            print("saving user: {}_{}: {}".format(user_id, user_name, len(all_illusts)))
            self.save_illusts(all_illusts, PurePath(save_path, "{}_{}".format(user_id, user_name)))
        return True

    def download_illusts(self):
        """download all illusts"""
        self.save_illusts(self.config.illusts, self.config.save_path)
        return True

    def download_users(self):
        """download all users"""

        self.save_users(self.config.users, self.config.save_path)
        return True

    def download_all(self):
        """download all files in config"""

        self.download_users()
        self.download_illusts()
