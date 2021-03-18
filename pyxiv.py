import json
import os
import sys
from pathlib import PurePath
from pyxivbase import PyxivBrowser, PyxivDatabase
import random

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


class PyxivSpider:
    def __init__(self, config_path):
        self.config: dict = json.load(config_path)
        self.browser = PyxivBrowser(self.config.get("proxies"), self.config.get("cookies"))
        self.db = PyxivDatabase(self.config.get("db_path"))
        self.save_path = self.config.get("save_path")

    @wrapper.log_calling_info
    def save_illust(self, illust_id, insert_user=True):
        """
        Args:
            illust_id: illust_id
            insert_user: True for insert user to database, False for not
        """
        illust = self.browser.get_illust(illust_id)
        if illust is None:
            if insert_user is True:
                # insert user
                user_id = illust.get("userId")
                user_name = illust.get("userName")
                self.db.insert_user(user_id, user_name)

            # insert illust
            illust_title = illust.get("illustTitle")
            self.db.insert_illust(illust_id, user_id, illust_title)

            # insert page
            pages = self.browser.get_illust_pages(illust_id)
            if pages:
                page_urls = [urls.get("original") for urls in pages]
                for page_id, page_url in enumerate(page_urls):
                    self.db.insert_page(illust_id, page_id, page_url)

    @wrapper.log_calling_info
    def save_user(self, user_id, user_name=None):
        """save a user with all illusts

        Args:
            user_id: user_id
            user_name: if given, it can save time to get user_name
        """
        # try get user_name
        if user_name is None:
            user = self.browser.get_user(user_id)
            if user:
                user_name = user.get("name")
            else:
                return None
        # insert user
        self.db.insert_user(user_id, user_name)
        user_all = self.browser.get_user_profile_all(user_id)
        if user_all:
            all_illust_ids = list(user_all.get("illusts").keys())
            for illust_id in all_illust_ids:
                self.save_illust(illust_id, False)

    def _get_user_info_by_followings(self, user_id) -> dict:
        """Return: {id: name}"""
        # be sure all followings are retrieved
        user_followings = {}  # {id: name}
        i = 0
        user_following = self.browser.get_user_following(user_id, i)
        while user_following:
            user_followings.update(
                {
                    int(user.get("userId")): user.get("userName")  # be sure int id
                    for user in user_following
                }
            )
            # try to gey next 50 followings
            i += 50
            user_following = self.browser.get_user_following(user_id, i)
        return user_followings

    def _get_user_info_by_recommends(self, user_id) -> dict:
        """Return: {id: name}"""
        # retrieve all recommends
        user_recommends = self.browser.get_user_recommends(user_id)
        user_recommends = {
            int(user.get("userId")): user.get("name")  # be sure int
            for user in user_recommends.get("users")
        }

        return user_recommends

    def _crawl(self, f_expand, seed_user_ids: set, max_user_num: int):
        """Crawl by f_expand

        Args:
            f_expand: how to expand seeds, callable, [param: user_id | return: {id: name}]
            seed_user_ids: A set of int or None, if not a empty set, the spider use it as primary seeds, 
            if None, it will use user ids exist in database for seeds.
            max_user_num: The max user num of crawling in one time

        Note:
            The max_user_num will exclude all existing user in database.
        """

        # get exist user ids
        exist_user_ids = set(row[0] for row in self.db.list_user_id_name())

        # prepare seeds
        if seed_user_ids is None:
            seed_user_ids = exist_user_ids.copy()
            # be sure to random choose seed user from database
            for _ in range(10000):
                random.shuffle(seed_user_ids)
            seed_user_ids = seed_user_ids[:10]  # use 10 for seeds
        seed_user_ids = set(map(int, seed_user_ids))  # be sure int id

        # BFS crawl critierion
        # queue: seed_user_ids: [(id, name), ...]
        # saved: saved_user_ids: [id, ...]
        # exist: exist_user_ids: [id, ...]
        seed_user_ids = set((i, None) for i in seed_user_ids)
        saved_user_ids = set()
        # for each seed user id, get its expand user ids
        while len(seed_user_ids) > 0 and len(saved_user_ids) < max_user_num:
            user_id, user_name = seed_user_ids.pop()

            # expand
            expanded_users: dict = f_expand(user_id)

            # new_user_ids = expanded - exist - saved
            new_user_ids = set(expanded_users.keys()).difference(exist_user_ids).difference(saved_user_ids)

            # add new_user_ids to seed_user_ids
            # and limit the length of seed_user_ids
            if len(seed_user_ids) < 100000:
                seed_user_ids.update([(id_, expanded_users.get(id_)) for id_ in new_user_ids])

            # check if save current user_id
            if not (user_id in exist_user_ids and user_id in saved_user_ids):
                self.save_user(user_id, user_name)
                saved_user_ids.add(user_id)

    def crawl_by_followings(self, seed_user_ids: set = None, max_user_num: int = 5000):
        """Crawl by followings

        Args:
            seed_user_ids: A set of int or None, if a set, the spider will iterate all user and get its followings, 
            if None, it will use random 10 user ids exist in database for seeds.
            max_user_num: The max user num of crawling in one time

        Note:
            The max_user_num will exclude all existing user in database.
        """

        return self._crawl(self._get_user_info_by_followings, seed_user_ids, max_user_num)

    def crawl_by_recommends(self, seed_user_ids: set = None, max_user_num: int = 5000):
        """Crawl by recommends

        Args:
            seed_user_ids: A set of int or None, if a set, the spider will iterate all user and get its recommends, 
            if None, it will use random 10 user ids exist in database for seeds.
            max_user_num: The max user num of crawling in one time

        Note:
            The max_user_num will exclude all existing user in database.
        """

        return self._crawl(self._get_user_info_by_recommends, seed_user_ids, max_user_num)
