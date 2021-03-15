import json
import os
import sys
from pathlib import PurePath

import requests

import wrapper


class PyxivConfig:
    def __init__(self):
        self.__proxies = {}
        self.__illusts = tuple()
        self.__users = tuple()
        self.__save_path = "."
        self.__R18 = False
        self.__cookies = {}

    @property
    def proxies(self):
        return self.__proxies.copy()

    @wrapper.log_setter_error
    @proxies.setter
    def proxies(self, value):
        self.__proxies = {"http": str(value["http"]), "https": str(value["https"])}

    @property
    def illusts(self):
        return self.__illusts

    @wrapper.log_setter_error
    @illusts.setter
    def illusts(self, value):
        self.__illusts = tuple(map(int, value))

    @property
    def users(self):
        return self.__users

    @wrapper.log_setter_error
    @users.setter
    def users(self, value):
        self.__users = tuple(map(int, value))

    @property
    def save_path(self):
        return self.__save_path

    @wrapper.log_setter_error
    @save_path.setter
    def save_path(self, value):
        self.__save_path = str(value)

    @property
    def R18(self):
        return self.__R18

    @wrapper.log_setter_error
    @R18.setter
    def R18(self, value):
        self.__R18 = bool(value)

    @property
    def cookies(self):
        return self.__cookies.copy()

    @wrapper.log_setter_error
    @cookies.setter
    def cookies(self, value):
        self.__cookies = {
            "PHPSESSID": str(value["PHPSESSID"]),
            "device_token": str(value["device_token"]),
            "privacy_policy_agreement": str(value["privacy_policy_agreement"])
        }

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

    url_top_illust = "https://www.pixiv.net/ajax/top/illust"  # ?mode=all # many many info in index page

    url_user = "https://www.pixiv.net/ajax/user/{user_id}"  # user simple info
    url_user_following = "https://www.pixiv.net/ajax/user/{user_id}/following"  # ?offset=0&limit=24&rest=show
    url_user_recommends = "https://www.pixiv.net/ajax/user/{user_id}/recommends"  # ?userNum=20&workNum=3&isR18=true
    url_user_profile_all = "https://www.pixiv.net/ajax/user/{user_id}/profile/all"  # user all illusts and details # 9930155
    url_user_profile_top = "https://www.pixiv.net/ajax/user/{user_id}/profile/top"
    url_user_illusts = "https://www.pixiv.net/ajax/user/{user_id}/illusts"  # ?ids[]=84502979"

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
        # print(self.session.cookies)

    def __del__(self):
        self.session.close()

    @wrapper.log_empty_return
    @wrapper.randsleep
    def _get_page(self, page_url) -> bytes:
        content = b""
        try:
            content = self.session.get(page_url).content
        except Exception as e:
            print(e.__class__, e, file=sys.stderr)
        return content

    @wrapper.log_empty_return
    @wrapper.randsleep
    def _get_illust(self, illust_id):
        json_ = self.session.get(PyxivBrowser.url_illust.format(illust_id=illust_id)).json()
        return {} if json_.get("error") is True else json_.get("body")

    @wrapper.log_empty_return
    @wrapper.randsleep
    def _get_illust_pages(self, illust_id):
        json_ = self.session.get(PyxivBrowser.url_illust_pages.format(illust_id=illust_id)).json()
        return {} if json_.get("error") is True else json_.get("body")

    @wrapper.log_empty_return
    @wrapper.randsleep
    def _get_user(self, user_id):
        json_ = self.session.get(PyxivBrowser.url_user.format(user_id=user_id)).json()
        return {} if json_.get("error") is True else json_.get("body")

    @wrapper.cookies_required
    @wrapper.log_empty_return
    @wrapper.randsleep
    def _get_user_following(self, user_id, offset, limit, rest="show"):
        json_ = self.session.get(
            PyxivBrowser.url_user_following.format(user_id=user_id),
            params={"offset": offset, "limit": limit, "rest": rest}
        ).json()
        return {} if json_.get("error") is True else json_.get("body")

    @wrapper.cookies_required
    @wrapper.log_empty_return
    @wrapper.randsleep
    def _get_user_recommends(self, user_id, userNum, workNum, isR18=True):
        json_ = self.session.get(
            PyxivBrowser.url_user_following.format(user_id=user_id),
            params={"userNum": userNum, "workNum": workNum, "isR18": isR18}
        ).json()
        return {} if json_.get("error") is True else json_.get("body")

    @wrapper.log_empty_return
    @wrapper.randsleep
    def _get_user_profile_all(self, user_id):
        json_ = self.session.get(PyxivBrowser.url_user_profile_all.format(user_id=user_id)).json()
        return {} if json_.get("error") is True else json_.get("body")

    @wrapper.log_empty_return
    @wrapper.randsleep
    def _get_user_profile_top(self, user_id):
        json_ = self.session.get(PyxivBrowser.url_user_profile_top.format(user_id=user_id)).json()
        return {} if json_.get("error") is True else json_.get("body")

    @wrapper.log_calling_info
    def save_page(self, page_url, save_path):
        """save page"""
        content = self._get_page(page_url)
        if content:
            with open(save_path, "wb") as f:
                f.write(content)

    @wrapper.log_calling_info
    def save_illust(self, illust_id, save_path):
        """save illust"""

        # check if R18 and set correct save path
        illust = self._get_illust(illust_id)
        if self.config.R18 and "R-18" in [tag.get("tag") for tag in illust.get("tags").get("tags")]:
            save_path = PurePath(save_path, "R-18")
        os.makedirs(save_path, exist_ok=True)

        # get all pages and check pages need to download
        illust_pages = self._get_illust_pages(illust_id)
        all_pages = {
            page.get("urls").get("original").split("/")[-1]: page.get("urls").get("original")
            for page in illust_pages
        }
        exist_pages = os.listdir(save_path)

        # save pages need to download
        pages_need_to_save = set(all_pages.keys()) - set(exist_pages)
        for page_id in pages_need_to_save:
            page_path = PurePath(save_path, page_id)
            self.save_page(all_pages[page_id], page_path)
        return True

    @wrapper.log_calling_info
    def save_user(self, user_id, save_path):
        user = self._get_user(user_id)
        user_all = self._get_user_profile_all(user_id)
        user_name = user.get("name")
        save_path = PurePath(save_path, "{}_{}".format(user_id, user_name))
        os.makedirs(save_path, exist_ok=True)
        illust_ids = list(user_all.get("illusts").keys())
        self.save_illusts(illust_ids, save_path)

    def save_illusts(self, illust_ids, save_path):
        for illust_id in illust_ids:
            self.save_illust(illust_id, save_path)
        return True

    def save_users(self, user_ids, save_path):
        for user_id in user_ids:
            self.save_user(user_id, save_path)
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
