import json
import os
import random
import shutil
import sys
from pathlib import PurePath

import wrapper
from pyxivbase import PyxivBrowser, PyxivConfig, PyxivDatabase


class PyxivSpider:
    """A Spider and Crawler for Pixiv

    Methods:
        save_*, update_*: save or update specified metadata to database
        crawl_*: automatic crawl metadata into databse
        retrieve_*: retrieve specified pictures from pixiv to local storage under config.save_path
        download_*: download specifed pictures from pixiv to local storage under any path
        copyto_*: copy pictures from database storage to specified local path
    """

    def __init__(self, config):
        self.config = config
        self.browser = PyxivBrowser(self.config.proxies, self.config.cookies)
        self.db = PyxivDatabase(self.config.db_path)

    # Crawling methods begin here
    # Used to save metadata to database, without downloading real pictures

    @wrapper.log_calling_info
    def _save_illust(self, illust_id, insert_user: bool):
        """
        Args:
            illust_id: illust_id
            insert_user: True for insert user to database, False for not
        """
        illust = self.browser.get_illust(illust_id)
        if illust:
            user_id = illust.get("userId")
            user_name = illust.get("userName")
            # insert user
            if insert_user is True:
                self.db.insert_user(user_id, user_name)

            # insert illust
            illust_title = illust.get("illustTitle")
            self.db.insert_illust(illust_id, user_id, illust_title)

            # insert page
            pages = self.browser.get_illust_pages(illust_id)
            if pages:
                page_urls = [page.get("urls").get("original") for page in pages]
                for page_id, page_url in enumerate(page_urls):
                    self.db.insert_page(illust_id, page_id, page_url)

            # insert tag
            tags = [tag.get("tag") for tag in illust.get("tags").get("tags")]
            for name in tags:
                self.db.insert_tag(name, illust_id)

        return None

    def save_illust(self, illust_id):
        return self._save_illust(illust_id, True)

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
                self._save_illust(illust_id, False)

    def update_all(self):
        """update all metadata stored in database, for each user"""
        users = self.db("SELECT id, name FROM user")
        for user_id, user_name in users:
            self.save_user(user_id, user_name)

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
        if user_recommends:
            user_recommends = {
                int(user.get("userId")): user.get("name")  # be sure int
                for user in user_recommends.get("users")
            }
        else:
            user_recommends = {}

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
        exist_user_ids = set(row[0] for row in self.db("SELECT id FROM user;"))

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
            if not (user_id in exist_user_ids or user_id in saved_user_ids):
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

    # Retrieve methods begin here
    # Used to retrieve pictures to config save_path by specific scope

    def _select_page_url_original_by_tag(self, names):
        """return (user.id, user.name, illust.id, page.page_id, page.url_original)"""
        illust_ids = []
        for name in names:
            illust_ids.append([row[0] for row in self.db("SELECT illust_id FROM tag WHERE name = ?", (name,))])

        # intersect
        result = set(illust_ids[0])
        for r in illust_ids[1:]:
            result.intersection_update(r)
        illust_ids = list(result)

        # get page_urls
        result = []
        for illust_id in illust_ids:
            result.extend(
                self.db(
                    """SELECT user.id, user.name, illust_id, page_id, url_original 
                        FROM page JOIN user JOIN illust 
                        ON page.illust_id=illust.id AND user.id=illust.user_id
                        WHERE illust_id = ?""", illust_id
                )
            )

        return list(result)

    def _select_page_url_original_by_user_name(self, user_name):
        """return (user.id, user.name, illust.id, page_id, page.url_original)"""
        return self.db(
            """SELECT user.id, user.name, illust.id, page_id, url_original 
                FROM user JOIN illust JOIN page
                ON page.illust_id=illust.id AND user.id=illust.user_id
                WHERE user.name = ?""", (user_name,)
        )

    def _select_page_url_original_by_user_id(self, user_id):
        """return (user.id, user.name, illust.id, page_id, page.url_original)"""
        return self.db(
            """SELECT user.id, user.name, illust.id, page_id, url_original 
                FROM user JOIN illust JOIN page
                ON page.illust_id=illust.id AND user.id=illust.user_id
                WHERE user.id = ?""", (user_id,)
        )

    def _select_page_url_original_by_illust_id(self, illust_id):
        """return (user.id, user.name, illust.id, page_id, page.url_original)"""
        return self.db(
            """SELECT user.id, user.name, illust.id, page_id, url_original 
                FROM user JOIN illust JOIN page
                ON page.illust_id=illust.id AND user.id=illust.user_id
                WHERE illust.id = ?""", (illust_id,)
        )

    @wrapper.log_calling_info
    def _download_page(self, page_url, save_path) -> bool:
        """download a page to save_path"""
        _pages = os.listdir(save_path)
        page_file_name = PurePath(save_path).name
        if page_file_name not in _pages:
            content = self.browser.get_page(page_url)
            if not content:
                return False
            with open(save_path, "wb") as f:
                f.write(content)
        return True

    def _download_retrieve(self, pages_need_to_save):
        """(user_id, user_name, illust_id, page_id, page_url)"""
        for user_id, user_name, illust_id, page_id, page_url in pages_need_to_save:
            save_path = PurePath(self.config.save_path, "{}_{}".format(user_id, user_name), illust_id, page_url.split("/")[-1])
            if self._download_page(page_url, save_path):
                self.db.update_page_save_path(illust_id, page_id, save_path.relative_to(self.config.save_path))

    def retrieve_by_tag(self, names: list):
        """names: tag names"""
        pages_need_to_save = self._select_page_url_original_by_tag(names)
        self._download_retrieve(pages_need_to_save)

    def retrieve_by_user_name(self, name: str):
        """name: user name"""
        pages_need_to_save = self._select_page_url_original_by_user_name(name)
        self._download_retrieve(pages_need_to_save)

    def retrieve_by_user_id(self, user_id: int):
        """user_id: id"""
        pages_need_to_save = self._select_page_url_original_by_user_id(user_id)
        self._download_retrieve(pages_need_to_save)

    def retrieve_by_illust_id(self, illust_id: int):
        """illust_id: id"""
        pages_need_to_save = self._select_page_url_original_by_illust_id(illust_id)
        self._download_retrieve(pages_need_to_save)

    def retrieve_all(self):
        """retrieve all pictures from pixiv"""
        pages_need_to_save = self._select_page_url_original_by_illust_id("*")
        self._download_retrieve(pages_need_to_save)

    # Download methods begin here
    # Used to download pictures easily to any local path

    def _download_illust(self, illust_id, save_dir, save_illust: bool, insert_user: bool):
        """save all pages of an illust"""

        if save_illust:
            self._save_illust(illust_id, insert_user)
        tags = [row[0] for row in self.db("SELECT name FROM tag WHERE illust_id = ?", illust_id)]
        page_urls = [row[0] for row in self.db("SELECT url_original FROM page WHERE illust_id = ?", illust_id)]
        if "R-18" in tags:
            save_dir = PurePath(save_dir, "R-18")
        for page_url in page_urls:
            self._download_page(page_url, PurePath(save_dir, page_url.split("/")[-1]))

    def download_illust(self, illust_id, save_dir):
        return self._download_illust(illust_id, save_dir, True, True)

    def download_user(self, user_id, save_dir):
        """save all iilust of a user"""

        self.save_user(user_id)
        user_name = self.db("SELECT name FROM user WHERE id = ?", user_id)[0][0]
        illust_ids = [row[0] for row in self.db("SELECT id FROM illust WHERE user_id = ?", user_id)]
        save_dir = PurePath(save_dir, user_id, user_name)
        for illust_id in illust_ids:
            self._download_illust(illust_id, save_dir, False, False)

    # Copyto methods begin here
    # Used to copy pictures to outer path

    def _select_page_save_path_by_tag(self, names):
        """return (page.save_path)"""
        illust_ids = []
        for name in names:
            illust_ids.append([row[0] for row in self.db("SELECT illust_id FROM tag WHERE name = ?", (name,))])

        # intersect
        result = set(illust_ids[0])
        for r in illust_ids[1:]:
            result.intersection_update(r)
        illust_ids = list(result)

        # get page_urls
        result = []
        for illust_id in illust_ids:
            result.extend(
                [row[0] for row in self.db(
                    "SELECT save_path FROM page WHERE illust_id = ? AND save_path != ''",
                    illust_id
                )]
            )

        return list(result)

    def _select_page_save_path_by_user_name(self, user_name):
        """return save_path"""
        return [row[0] for row in self.db(
            """SELECT save_path
                FROM user JOIN illust JOIN page
                ON page.illust_id=illust.id AND user.id=illust.user_id
                WHERE user.name = ? AND save_path != ''""", (user_name,)
        )]

    def _select_page_save_path_by_user_id(self, user_id):
        """return save_path"""
        return [row[0] for row in self.db(
            """SELECT save_path
                FROM user JOIN illust JOIN page
                ON page.illust_id=illust.id AND user.id=illust.user_id
                WHERE user.id = ? AND save_path != ''""", (user_id,)
        )]

    def _select_page_save_path_by_illust_id(self, illust_id):
        """return save_path"""
        return [row[0] for row in self.db("SELECT save_path FROM page WHERE illust_id = ? AND save_path != ''", (illust_id,))]

    def _copyto(self, src_files, dest_dir):
        for path in src_files:
            print("Copy File: {} to {}".format(path, dest_dir))
            shutil.copy(PurePath(self.config.save_path, path), PurePath(dest_dir, PurePath(path).name))

    def copyto_by_tag(self, dest_dir, names):
        save_paths = self._select_page_save_path_by_tag(names)
        self._copyto(save_paths, dest_dir)

    def copyto_by_user_name(self, dest_dir, name):
        save_paths = self._select_page_save_path_by_user_name(name)
        self._copyto(save_paths, dest_dir)

    def copyto_by_user_id(self, dest_dir, user_id):
        save_paths = self._select_page_save_path_by_user_id(user_id)
        self._copyto(save_paths, dest_dir)

    def copyto_by_illust_id(self, dest_dir, illust_id):
        save_paths = self._select_page_save_path_by_illust_id(illust_id)
        self._copyto(save_paths, dest_dir)
