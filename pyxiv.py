import json
import os
import sys
from pathlib import PurePath
from pyxivbase import PyxivBrowser, PyxivDatabase

import wrapper


class PyxivDownloader:
    def __init__(self, config_path):
        self.config: dict = json.load(config_path)
        self.db = PyxivDatabase(self.config.get("db_path"))
        self.browser = PyxivBrowser(self.config.get("proxies"), self.config.get("cookies"))
    # functions of saving

    @wrapper.log_calling_info
    def save_page(self, page_url, save_path):
        """save page"""
        content = self.browser.get_page(page_url)
        if content:
            with open(save_path, "wb") as f:
                f.write(content)
            return True
        return False

    @wrapper.log_calling_info
    def save_illust(self, illust_id, save_path):
        """save all pages of an illust"""

        # check if R18 and set correct save path
        illust = self.browser.get_illust(illust_id)
        os.makedirs(PurePath(save_path, illust.get("illustId")), exist_ok=True)

        # get all pages and check pages need to download
        illust_pages = self.browser.get_illust_pages(illust_id)
        all_pages = [
            [page.get("urls").get("original").split("/")[-1],
             page.get("urls").get("original")]
            for page in illust_pages
        ]
        exist_pages = os.listdir(save_path)

        # save pages need to download
        pages_need_to_save = set(all_pages.keys()) - set(exist_pages)
        for page_id in pages_need_to_save:
            page_path = PurePath(save_path, page_id)
            self.save_page(all_pages[page_id], page_path)
        return True

    @wrapper.log_calling_info
    def save_user(self, user_id, save_path):
        """save all illusts of a user"""
        user = self.browser.get_user(user_id)
        user_all = self.browser.get_user_profile_all(user_id)
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

    def save_followings(self, user_id, save_path):
        """save all following users of a user"""
        user_following = self.browser.get_user_following(user_id, ..., ...)
        following_ids = user_following.get(...)

    def save_recommends(self, user_id, save_path):
        """save all recommended users of a user"""
        user_recommends = self.browser.get_user_recommends(user_id, ..., ...)
        recommend_ids = user_recommends.get(...)

    # functions for config

    def download_illusts(self):
        """download all illusts"""
        self.save_illusts(self.config.illusts, self.config.save_path)
        return True

    def download_users(self):
        """download all users"""

        self.save_users(self.config.users, self.config.save_path)
        return True

    def download_followings(self):
        ...

    def download_recommends(self):
        ...

    def download_all(self):
        """download all files in config"""

        self.download_users()
        self.download_illusts()


class PyxivSpider:
    ...
