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
        download_*: download specifed pictures to local path
    """

    def __init__(self, config):
        self.config = config
        self.browser = PyxivBrowser(self.config.proxies, self.config.cookies)
        self.db = PyxivDatabase(self.config.db_path)

    # Crawling methods begin here
    # Used to save metadata to database, without downloading real pictures

    @wrapper.log_calling_info
    def save_illust(self, illust_id) -> bool:
        """Store or update full information of an illust, may affect all tables in database

        Args:
            illust_id: illust_id

        Returns:
            bool: Return True if the illust information has been fully stored in database, else False
        """
        illust = self.browser.get_illust(illust_id)
        pages = self.browser.get_illust_pages(illust_id)
        # only store complete illust information
        if illust and pages:
            # insert user
            user_id = illust.get("userId")
            user_name = illust.get("userName")
            self.db.insert_user(user_id, user_name)

            # insert illust
            illust_title = illust.get("title")
            illust_description = illust.get("description")
            bookmark_count = illust.get("bookmarkCount")
            like_count = illust.get("likeCount")
            view_count = illust.get("viewCount")
            self.db.insert_illust(illust_id, illust_title, illust_description, bookmark_count, like_count, view_count, user_id)

            # insert page
            page_urls = [page.get("urls").get("original") for page in pages]
            for page_id, url_original in enumerate(page_urls):
                self.db.insert_page(illust_id, page_id, url_original)

            # insert tag
            tags = [tag.get("tag") for tag in illust.get("tags").get("tags")]
            for name in tags:
                self.db.insert_tag(name, illust_id)

            return True
        else:
            return False

    @wrapper.log_calling_info
    def save_user(self, user_id) -> bool:
        """Save illusts information of a user, excluding existing illusts

        Returns:
            bool: Return True if the user information has been stored in database, else False
        """
        result = False
        user_all = self.browser.get_user_profile_all(user_id)
        if user_all:
            all_illust_ids = set(map(int, user_all.get("illusts").keys()))
            exist_illust_ids = [row[0] for row in self.db("SELECT id FROM illust WHERE user_id = ?", (user_id,))]
            if exist_illust_ids:
                result = True
            for illust_id in all_illust_ids.difference(exist_illust_ids):
                if self.save_illust(illust_id):
                    result = True
        return result

    def save_top_illust(
            self, mode="all",
            f_tags=True, f_follow=True, f_recommend=True,
            f_recommend_by_tag=True, f_recommend_user=True, f_trending_tags=True):
        """Save daily recommended illusts in index page

        Args:
            mode: "all" | "r18"
            f_*: flags to control save content, True for save, False for not.
        """
        top_illust = self.browser.get_top_illust(mode)
        if top_illust:
            page_info = top_illust.get("page")
            exist_illust_ids = [row[0] for row in self.db("SELECT id FROM illust")]
            illust_ids = []
            if f_tags:
                for e in page_info.get("tags"):
                    illust_ids.extend(e.get("ids"))
            if f_follow:
                illust_ids.extend(page_info.get("follow"))
            if f_recommend:
                illust_ids.extend(page_info.get("recommend").get("ids"))
            if f_recommend_by_tag:
                for e in page_info.get("recommendByTag"):
                    illust_ids.extend(e.get("ids"))
            if f_recommend_user:
                for e in page_info.get("recommendUser"):
                    illust_ids.extend(e.get("illustIds"))
            if f_trending_tags:
                for e in page_info.get("trendingTags"):
                    illust_ids.extend(e.get("ids"))

            # exclude exist
            illust_ids = set(map(int, illust_ids)).difference(exist_illust_ids)
            for illust_id in illust_ids:
                self.save_illust(illust_id)

    def save_all(self):
        """Save all illusts information of all users stored in database, excluding existing illusts"""
        user_ids = [row[0] for row in self.db("SELECT id FROM user")]
        for user_id in user_ids:
            self.save_user(user_id)

    def update_illusts_info(self):
        """Update information of all illusts stored in database"""

        illust_ids = [row[0] for row in self.db("SELECT id FROM illust")]
        for illust_id in illust_ids:
            self.save_illust(illust_id)

    def _get_user_id_by_followings(self, user_id) -> list:
        """Return: [int(id), ...]"""
        # be sure all followings are retrieved
        user_followings = []  # int(id)
        i = 0
        user_following = self.browser.get_user_following(user_id, i)
        while user_following:
            for user in user_following:
                user_followings.append(int(user.get("userId")))  # int id
            # try to gey next 50 followings
            i += 50
            user_following = self.browser.get_user_following(user_id, i)
        return user_followings

    def _get_user_id_by_recommends(self, user_id) -> list:
        """Return: [int(id), ...]"""
        # retrieve 100 recommends
        user_recommends = self.browser.get_user_recommends(user_id)
        if user_recommends:
            user_recommends = [int(user.get("userId")) for user in user_recommends.get("users")]  # int id
        else:
            user_recommends = []

        return user_recommends

    def _crawl(self, f_expand, seed_user_ids: set, max_user_num: int):
        """Crawl by f_expand

        Args:
            f_expand: how to expand seeds, callable, [param: user_id | return: [int(id), ...]]
            seed_user_ids: A set of int or None, if not a empty set, the spider use it as primary seeds,
            if None, it will use user ids exist in database for seeds.
            max_user_num: The max user num of crawling in one time

        Note:
            The max_user_num will exclude all existing user in database.
        """

        # get exist user ids
        exist_user_ids = list(row[0] for row in self.db("SELECT id FROM user;"))

        # prepare seeds
        if seed_user_ids is None:
            seed_user_ids = exist_user_ids.copy()
            # be sure to random choose seed user from database
            for _ in range(10000):
                random.shuffle(seed_user_ids)
            seed_user_ids = seed_user_ids[: 10]  # use 10 for seeds

        # BFS crawl critierion
        # queue: seed_user_ids: [id, ...]
        # saved: saved_user_ids: [id, ...]
        # exist: exist_user_ids: [id, ...]
        seed_user_ids = set(map(int, seed_user_ids))  # be sure int id
        saved_user_ids = set()
        exist_user_ids = set(exist_user_ids)
        # for each seed user id, get its expand user ids
        while len(seed_user_ids) > 0 and len(saved_user_ids) < max_user_num:
            user_id = seed_user_ids.pop()

            # add new_user_ids to seed_user_ids
            # and limit the length of seed_user_ids
            if len(seed_user_ids) < 100000:
                seed_user_ids.update(
                    set(f_expand(user_id))
                    .difference(exist_user_ids)
                    .difference(saved_user_ids)
                )

            # check if save current user_id
            if not (user_id in exist_user_ids or user_id in saved_user_ids):
                if self.save_user(user_id):
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

        return self._crawl(self._get_user_id_by_followings, seed_user_ids, max_user_num)

    def crawl_by_recommends(self, seed_user_ids: set = None, max_user_num: int = 5000):
        """Crawl by recommends

        Args:
            seed_user_ids: A set of int or None, if a set, the spider will iterate all user and get its recommends,
            if None, it will use random 10 user ids exist in database for seeds.
            max_user_num: The max user num of crawling in one time

        Note:
            The max_user_num will exclude all existing user in database.
        """

        return self._crawl(self._get_user_id_by_recommends, seed_user_ids, max_user_num)

    # Retrieve methods begin here
    # Used to retrieve pictures to config save_path by specific scope

    def _select_page_url_original_by_tag(self, names):
        """return (user.id, user.name, illust.id, page.page_id, page.url_original)"""
        illust_ids = []
        for name in names:
            illust_ids.append([row[0] for row in self.db("SELECT illust_id FROM tag WHERE name = ?;", (name,))])

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
                        WHERE illust_id = ?;""", (illust_id, )
                )
            )

        return list(result)

    def _select_page_url_original_by_user_id(self, user_id):
        """return (user.id, user.name, illust.id, page_id, page.url_original)"""
        return self.db(
            """SELECT user.id, user.name, illust.id, page_id, url_original
                FROM user JOIN illust JOIN page
                ON page.illust_id=illust.id AND user.id=illust.user_id
                WHERE user.id = ?;""", (user_id,)
        )

    def _select_page_url_original_by_illust_id(self, illust_id):
        """return (user.id, user.name, illust.id, page_id, page.url_original)"""
        return self.db(
            """SELECT user.id, user.name, illust.id, page_id, url_original
                FROM user JOIN illust JOIN page
                ON page.illust_id=illust.id AND user.id=illust.user_id
                WHERE illust.id = ?;""", (illust_id,)
        )

    # Download methods begin here
    # Used to download pictures to local path
    # It will first search database for illust information
    # If not found, save_illust will be called before downloading the illust

    @wrapper.log_calling_info
    def download_page(self, page_url, save_dir) -> bool:
        """Download a page to save_dir"""
        os.makedirs(save_dir, exist_ok=True)
        file_name = page_url.split("/")[-1]
        if file_name in os.listdir(save_dir):
            return True
        else:
            content = self.browser.get_page(page_url)
            if content:
                with open(PurePath(save_dir, file_name), "wb") as f:
                    f.write(content)
                return True
            else:
                return False

    def download_illust(self, illust_id, save_dir) -> bool:
        """Save all pages of an illust

        Returns:
            bool: Return True if the illust information is stored in database, else False
        """

        # try to retrieve illust information in database or save it
        if not self.db("SELECT id FROM illust WHERE id = ?;", (illust_id, )):
            if not self.save_illust(illust_id):
                return False
        page_urls = [row[0] for row in self.db("SELECT url_original FROM page WHERE illust_id = ?;", (illust_id, ))]
        tags = [row[0] for row in self.db("SELECT name FROM tag WHERE illust_id = ?", (illust_id,))]
        if "R-18" in tags:
            save_dir = PurePath(save_dir, "R-18")
        for page_url in page_urls:
            self.download_page(page_url, save_dir)
        return True

    def download_user(self, user_id, save_dir) -> bool:
        """Save all illust of a user

        Returns:
            bool: Return True if the user information has been stored in database, else False
        """

        # fisrt save_user
        if self.save_user(user_id):
            user_name = self.db("SELECT name FROM user WHERE id = ?;", (user_id,))[0][0]
            illust_ids = [row[0] for row in self.db("SELECT id FROM illust WHERE user_id = ?;", (user_id,))]
            save_dir = PurePath(save_dir, "{}_{}".format(user_id, user_name))
            for illust_id in illust_ids:
                self.download_illust(illust_id, save_dir)
            return True
        else:
            return False

    def download_popular(self, save_dir, mode="all", top_num=100):
        ...
        # TODO
