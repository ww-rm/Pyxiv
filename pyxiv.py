import os
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import wrapper
from pyxivbase import PyxivBrowser, PyxivConfig, PyxivDatabase


class PyxivSpider:
    """A Spider and Crawler for Pixiv

    Methods:
        save_*, update_*: save or update specified metadata to database
        crawl_*: automatic crawl metadata into databse
        download_*: download specifed pictures to local path
    """

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36",
    }

    def __init__(self, config_path):
        self.config = PyxivConfig(config_path)
        self.browser = PyxivBrowser(self.config.proxies, self.config.cookies)
        self.db = PyxivDatabase(self.config.db_path)

        self.browser.headers.update(self.headers)

    # Save methods begin here
    # Used to save metadata to database, without downloading real pictures

    def search_cache(self, keywords: list = None, scope="tag", mode="all", match="fuzzy", query="and", order="like"):
        """Search database for cache result

        Args:
            keywords: A list contain keywords to search, can be None or empty list for all result
            scope: "tag", "titledesc", "all"
            mode: "safe", "r18", "all"
            match: "fuzzy", "exactly"
            query: "and", "or"
            order: "like", "bookmark", "view"

        Returns:
            A list consist of two-tuples, like (illust_id, key), where key is specified by order
        """

        # check value
        scope_values = ["tag", "titledesc", "all"]
        mode_values = ["safe", "r18", "all"]
        match_values = ["fuzzy", "exactly"]
        query_values = ["and", "or"]
        order_values = ["like", "bookmark", "view"]
        if scope not in scope_values:
            raise ValueError("Incorrect scope value: {}".format(scope))
        if mode not in mode_values:
            raise ValueError("Incorrect mode value: {}".format(mode))
        if match not in match_values:
            raise ValueError("Incorrect match value: {}".format(match))
        if query not in query_values:
            raise ValueError("Incorrect query value: {}".format(query))
        if order not in order_values:
            raise ValueError("Incorrect order value: {}".format(order))

        # prepare for sql command
        o_value = {
            "like": "like_count",
            "bookmark": "bookmark_count",
            "view": "view_count"
        }
        m_where = {
            "fuzzy": {
                "tag": " (name LIKE ?) ",
                "td": " (title LIKE ? OR description LIKE ?) "
            },
            "exactly": {
                "tag": " (name = ?) ",
                "td": " (title = ? OR description = ?) "
            }
        }

        # sql command
        sql_full = "SELECT id, {order} FROM illust;".format(order=o_value[order])
        sql_tag = "SELECT DISTINCT id, {order} FROM illust JOIN tag ON illust.id = tag.illust_id WHERE {where};".format(
            order=o_value[order],
            where=m_where[match]["tag"])
        sql_td = "SELECT id, {order} FROM illust WHERE {where};".format(
            order=o_value[order],
            where=m_where[match]["td"]
        )
        sql_r18 = "SELECT id, {order} FROM illust WHERE x_restrict > 0;".format(order=o_value[order])

        result_set = set(self.db(sql_full))

        # get tag and td sets
        if keywords:
            # fuzzy query
            if match == "fuzzy":
                keywords = ["%"+e+"%" for e in keywords]

            tag_sets = []
            td_sets = []
            for keyword in keywords:
                tag_sets.append(set(self.db(sql_tag, (keyword,))))
                td_sets.append(set(self.db(sql_td, (keyword, keyword))))
            tag_set = tag_sets[0].copy()
            td_set = td_sets[0].copy()

            # keywords AND or OR
            if query == "and":
                for set_ in tag_sets:
                    tag_set.intersection_update(set_)
                for set_ in td_sets:
                    td_set.intersection_update(set_)
            else:
                for set_ in tag_sets:
                    tag_set.update(set_)
                for set_ in td_sets:
                    td_set.update(set_)

            # {full} intersect ({tag} union {td})
            if scope == "tag":
                result_set.intersection_update(tag_set)
            elif scope == "titledesc":
                result_set.intersection_update(td_set)
            else:
                result_set.intersection_update(tag_set.union(td_set))

        # except or intersect R18 set
        r18_set = set(self.db(sql_r18))
        if mode == "safe":
            result_set.difference_update(r18_set)
        elif mode == "r18":
            result_set.intersection_update(r18_set)

        # descend result set
        result = sorted(result_set, key=lambda e: e[1], reverse=True)
        return result

    @wrapper.log_calling_info()
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
            x_restrict = illust.get("xRestrict")
            upload_date = illust.get("uploadDate")
            self.db.insert_illust(
                illust_id, illust_title, illust_description,
                bookmark_count, like_count, view_count,
                user_id, x_restrict, upload_date
            )

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

    @wrapper.log_calling_info()
    def save_user(self, user_id) -> bool:
        """Save illusts information of a user, excluding existing illusts

        Returns:
            bool: Return True if the user information has been stored in database, else False
        """
        result = False
        user_all = self.browser.get_user_profile_all(user_id)
        if user_all:
            all_illust_ids = set(map(int, user_all.get("illusts")))
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

        illust_ids = self.db("SELECT id, upload_date, last_update_date FROM illust")
        now_date = datetime.now(timezone(timedelta()))
        illust_ids_need_to_update = []
        for illust_id, upload_date, last_update_date in illust_ids:
            upload_date = datetime.fromisoformat(upload_date)
            last_update_date = datetime.fromisoformat(last_update_date)
            if (now_date - upload_date).days <= 7:
                if (now_date - last_update_date).days > 1:
                    illust_ids_need_to_update.append(illust_id)
            elif (now_date - upload_date).days <= 30:
                if (now_date - last_update_date).days > 7:
                    illust_ids_need_to_update.append(illust_id)
            elif (now_date - upload_date).days <= 365:
                if (now_date - last_update_date).days > 30:
                    illust_ids_need_to_update.append(illust_id)
            elif (now_date - upload_date).days <= 365*5:
                if (now_date - last_update_date).days > 30*3:
                    illust_ids_need_to_update.append(illust_id)
            else:
                if (now_date - last_update_date).days > 30*6:
                    illust_ids_need_to_update.append(illust_id)

        print("{} illusts need to be updated...".format(len(illust_ids_need_to_update)))
        for illust_id in illust_ids_need_to_update:
            # XXX: self.save_illust(illust_id)
            print(illust_id)
            # just update illust information, without pages
            illust = self.browser.get_illust(illust_id)
            if illust:
                user_id = illust.get("userId")
                # update illust
                illust_title = illust.get("title")
                illust_description = illust.get("description")
                bookmark_count = illust.get("bookmarkCount")
                like_count = illust.get("likeCount")
                view_count = illust.get("viewCount")
                x_restrict = illust.get("xRestrict")
                upload_date = illust.get("uploadDate")
                self.db.insert_illust(
                    illust_id, illust_title, illust_description,
                    bookmark_count, like_count, view_count,
                    user_id, x_restrict, upload_date
                )
                # update tag
                tags = [tag.get("tag") for tag in illust.get("tags").get("tags")]
                for name in tags:
                    self.db.insert_tag(name, illust_id)

    # Crawl methods begin here
    # Used to automatic crawl metadata
    # by user followings or pixiv recommends

    def _get_user_id_by_followings(self, user_id) -> list:
        """Return: [int(id), ...]"""
        # be sure all followings are retrieved
        user_followings = []
        i = 0
        user_following = self.browser.get_user_following(user_id, i)
        while user_following and user_following.get("users"):  # non-empty return and non-empty users list
            for user in user_following.get("users"):
                user_followings.append(user.get("userId"))
            # try to gey next 50 followings
            i += 50
            user_following = self.browser.get_user_following(user_id, i)  # next followings
        return user_followings

    def _get_user_id_by_recommends(self, user_id) -> list:
        """Return: [int(id), ...]"""
        # retrieve 100 recommends
        user_recommends = self.browser.get_user_recommends(user_id)
        if user_recommends:
            user_recommends = [user.get("userId") for user in user_recommends.get("users")]
        else:
            user_recommends = []
        return user_recommends

    def _crawl_by_user(self, f_expand, seed_user_ids: set, max_user_num: int):
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
        exist_user_ids = list(row[0] for row in self.db("SELECT DISTINCT user_id FROM illust ORDER BY bookmark_count DESC;"))

        # prepare seeds
        if seed_user_ids is None:
            seed_user_ids = exist_user_ids[: 1000].copy()
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
            if len(seed_user_ids) < 1000000:
                seed_user_ids.update(
                    set(map(int, f_expand(user_id)))  # be sure int id
                    .difference(exist_user_ids)
                    .difference(saved_user_ids)
                )

            # check if save current user_id
            if not (user_id in exist_user_ids or user_id in saved_user_ids):
                if self.save_user(user_id):
                    saved_user_ids.add(user_id)
                else:
                    seed_user_ids.add(user_id)  # not remove it

    def crawl_by_user_followings(self, seed_user_ids: set = None, max_user_num: int = 300):
        """Crawl by followings

        Args:
            seed_user_ids: A set of int or None, if a set, the spider will iterate all user and get its followings,
            if None, it will use random 10 user ids exist in database for seeds.
            max_user_num: The max user num of crawling in one time

        Note:
            The max_user_num will exclude all existing user in database.
        """

        return self._crawl_by_user(self._get_user_id_by_followings, seed_user_ids, max_user_num)

    def crawl_by_user_recommends(self, seed_user_ids: set = None, max_user_num: int = 300):
        """Crawl by recommends

        Args:
            seed_user_ids: A set of int or None, if a set, the spider will iterate all user and get its recommends,
            if None, it will use random 10 user ids exist in database for seeds.
            max_user_num: The max user num of crawling in one time

        Note:
            The max_user_num will exclude all existing user in database.
        """

        return self._crawl_by_user(self._get_user_id_by_recommends, seed_user_ids, max_user_num)

    def crawl_by_illust_recommends(self, seed_illust_ids: set = None, max_illust_num: int = 30000):
        """Crawl by illust recommends

        Args:
            seed_illust_ids: A set of int or None, if not a empty set, the spider use it as primary seeds,
            if None, it will use illust ids exist in database for seeds.
            max_illust_num: The max user num of crawling in one time

        Note:
            The max_illust_num will exclude all existing illust in database.
        """

        # get exist user ids
        exist_illust_ids = list(row[0] for row in self.db("SELECT id FROM illust ORDER BY bookmark_count DESC;"))

        # prepare seeds
        if seed_illust_ids is None:
            seed_illust_ids = exist_illust_ids[: 10000].copy()
            # be sure to random choose seed user from database
            for _ in range(100000):
                random.shuffle(seed_illust_ids)
            seed_illust_ids = seed_illust_ids[: 100]  # use 100 for seeds

        # BFS crawl critierion
        # queue: seed_illust_ids: [id, ...]
        # saved: saved_illust_ids: [id, ...]
        # exist: exist_illust_ids: [id, ...]
        seed_illust_ids = set(map(int, seed_illust_ids))  # be sure int id
        saved_illust_ids = set()
        exist_illust_ids = set(exist_illust_ids)
        # for each seed illust id, get its expand illust ids
        while len(seed_illust_ids) > 0 and len(saved_illust_ids) < max_illust_num:
            illust_id = seed_illust_ids.pop()

            # add new_user_ids to seed_illust_ids
            # and limit the length of seed_illust_ids
            if len(seed_illust_ids) < 1000000:
                illust_recommend_init = self.browser.get_illust_recommend_init(illust_id)
                if illust_recommend_init:
                    seed_illust_ids.update(
                        set(map(int, illust_recommend_init.get("details")))  # actually a dict or empty list # be sure int id
                        .difference(exist_illust_ids)
                        .difference(saved_illust_ids)
                    )

            # check if save current illust_id
            if not (illust_id in exist_illust_ids or illust_id in saved_illust_ids):
                if self.save_illust(illust_id):
                    saved_illust_ids.add(illust_id)
                else:
                    seed_illust_ids.add(illust_id)  # not remove it

    # Download methods begin here
    # Used to download pictures to local path
    # It will first search database for illust information
    # If not found, save_illust will be called before downloading the illust

    @wrapper.log_calling_info()
    def download_page(self, page_url, save_dir) -> bool:
        """Download a page to save_dir"""
        os.makedirs(save_dir, exist_ok=True)
        file_name = page_url.split("/")[-1]
        if file_name in os.listdir(save_dir):
            return True
        else:
            content = self.browser.get_page(page_url)
            if content:
                with open(Path(save_dir, file_name), "wb") as f:
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
        x_restrict, *_ = self.db("SELECT x_restrict FROM illust WHERE id = ?", (illust_id,))[0]
        if x_restrict > 0:
            save_dir = Path(save_dir, "R-18")
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
            save_dir = Path(save_dir, "{}_{}".format(user_id, user_name))
            for illust_id in illust_ids:
                self.download_illust(illust_id, save_dir)
            return True
        else:
            return False

    def download_ranking(self, save_dir, p=1, content="illust", mode="monthly", date=None):
        """Get ranking, limit 50 illusts info in one page

        Args:
            p: page number, >= 1
            content:
                "all": mode[Any]
                "illust": mode["daily", "weekly", "daily_r18", "weekly_r18", "monthly", "rookie"]
                "ugoira"(動イラスト): mode["daily", "weekly", "daily_r18", "weekly_r18"]
                "manga": mode["daily", "weekly", "daily_r18", "weekly_r18", "monthly", "rookie"]
            mode: ["daily", "weekly", "daily_r18", "weekly_r18", "monthly", "rookie",
                "original", "male", "male_r18", "female", "female_r18"]
            date: ranking date, example: 20210319, None means the newest

        Note: May need cookies to get r18 ranking
        """
        ranking = self.browser.get_ranking(p, content, mode, date)
        if ranking:
            save_dir = Path(save_dir, "ranking_{}".format(ranking.get("date")))
            illust_ids = [e.get("illust_id") for e in ranking.get("contents")]
            for illust_id in illust_ids:
                self.download_illust(illust_id, save_dir)

    def download_search_illustrations(self, save_dir):
        raise NotImplementedError

    def download_illusts(self, illust_ids, save_dir, bookmark_illusts: bool = False, bookmark_users: bool = False):
        """Download illusts, aimed to fit indexer

        Args:
            illust_ids: list of illust ids to download, will first get metadata to database if any not in database
            save_dir: save dir
            bookmark_illusts: whether add bookmarks to all illusts downloaded
            bookmark_users: whether add bookmarks to all users of illusts downloaded
        """
        success_ids = []
        for illust_id in illust_ids:
            if self.download_illust(illust_id, save_dir):
                success_ids.append(illust_id)

        illusts_info = []
        for illust_id in success_ids:
            illusts_info.extend(self.db("SELECT id, user_id FROM illust WHERE id = ?;", (illust_id,)))
        if bookmark_illusts:
            for illust_id, _ in illusts_info:
                self.browser.post_illusts_bookmarks_add(illust_id)
        if bookmark_users:
            for _, user_id in illusts_info:
                self.browser.post_bookmark_add(user_id)

        print("Total: {}".format(len(illust_ids)))
        print("Success: {}".format(len(success_ids)))


if __name__ == "__main__":
    pass
    # spider = PyxivSpider("./config.json")
    # rows = spider.search_cache(["女の子"], mode="r18")
    # print(len(rows))
    # spider.download_ranking("./top50")
