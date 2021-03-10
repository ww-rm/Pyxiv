import os
import pathlib
import random
import sys
from time import sleep

import requests

from config import PyxivConfig


class Pyxiv:
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
        self.session.headers = Pyxiv.headers
        self.session.proxies = config.proxies

    def randsleep(self, max_sec=3):
        sleep(random.random()*max_sec)

    def get_pages(self, illust_id):
        """
        get all page urls for a illust

        {
            "1234567_p0.jpg": "xxxxxxxxxxxxxxx/1234567_p0.jpg"
        }
        """
        pages = {}

        response = self.session.get(Pyxiv.url_illust_pages.format(illust_id=illust_id))
        self.randsleep()
        json_ = response.json()

        if json_.get("error") is True:
            print("Error: get_pages illust_id: {}".format(illust_id), file=sys.stderr)
        else:
            for illust in json_.get("body"):
                img_url = illust.get("urls").get("original")
                pages[img_url.split("/")[-1]] = img_url

        return pages

    def get_illusts(self, user_id):
        """
        get all illusts id for a user

        [pid1, pid2, pid3, ...]
        """
        illusts = []

        response = self.session.get(Pyxiv.url_user_all.format(user_id=user_id))
        self.randsleep()
        json_ = response.json()

        if json_.get("error") is True:
            print("Error: get_illusts user_id: {}".format(user_id), file=sys.stderr)
            return False

        illusts = list(json_.get("body").get("illusts").keys())
        return illusts

    def get_username_by_id(self, user_id):
        response = self.session.get(Pyxiv.url_user.format(user_id=user_id))
        self.randsleep()
        json_ = response.json()
        username = "unknown"

        if json_.get("error") is True:
            print("Error: get_username_by_id user_id: {}".format(user_id), file=sys.stderr)
        else:
            username = json_.get("body").get("name")

        return username

    def get_username_userid_by_illust(self, illust_id):
        response = self.session.get(Pyxiv.url_illust.format(illust_id=illust_id))
        self.randsleep()
        json_ = response.json()
        username = "unknown"
        user_id = 0

        if json_.get("error") is True:
            print("Error: get_username_by_illust illust_id: {}".format(illust_id, file=sys.stderr))
        else:
            username = json_.get("body").get("userName")
            user_id = json_.get("body").get("userId")

        return (username, user_id)

    def save_illust(self, illust_id: str, save_path: str):
        """save illust"""

        pages = self.get_pages(illust_id)
        exist_pages = os.listdir(save_path)

        pages_need_to_save = set(pages.keys()) - set(exist_pages)
        for page_id in pages_need_to_save:
            page_path = pathlib.PurePath(save_path, page_id)
            response = self.session.get(pages[page_id])
            self.randsleep()
            print("\tsaving page: {}".format(page_path))
            with open(page_path, "wb") as f:
                f.write(response.content)
        return True

    def download_illusts(self):
        for illust_id in self.config.illusts:
            username, user_id = self.get_username_userid_by_illust(illust_id)
            print("saving illust: {}_{}".format(user_id, username))
            save_path = pathlib.PurePath(self.config.save_path, "{}_{}".format(user_id, username))
            os.makedirs(save_path, exist_ok=True)
            self.save_illust(illust_id, save_path)
        return True

    def download_users(self):
        for user_id in self.config.users:
            username = self.get_username_by_id(user_id)
            save_path = pathlib.PurePath(self.config.save_path, "{}_{}".format(user_id, username))
            os.makedirs(save_path, exist_ok=True)

            print("saving user: {}_{}".format(user_id, username))
            illusts = self.get_illusts(user_id)
            for illust_id in illusts:
                self.save_illust(illust_id, save_path)
        return True

    def download_all(self):
        """download all files in config"""

        self.download_users()
        self.download_illusts()
