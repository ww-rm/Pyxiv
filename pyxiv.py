import os
import random
from datetime import datetime, timedelta, timezone
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

    def __init__(self, config: PyxivConfig):
        self.config = config
        self.browser = PyxivBrowser(self.config.proxies, self.config.cookies)
        self.db = PyxivDatabase(self.config.db_path)

    # Save methods begin here
    # Used to save metadata to database, without downloading real pictures

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
            upload_date = illust.get("uploadDate")
            self.db.insert_illust(
                illust_id, illust_title, illust_description,
                bookmark_count, like_count, view_count,
                user_id, upload_date
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
        now_date = datetime.now(timezone(timedelta())).replace(microsecond=0)
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
                upload_date = illust.get("uploadDate")
                self.db.insert_illust(
                    illust_id, illust_title, illust_description,
                    bookmark_count, like_count, view_count,
                    user_id, upload_date
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
                    set(f_expand(user_id))
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
                        set(illust_recommend_init.get("details"))  # actually a dict or empty list
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
            save_dir = PurePath(save_dir, "ranking_{}".format(ranking.get("date")))
            illust_ids = [e.get("illust_id") for e in ranking.get("contents")]
            for illust_id in illust_ids:
                self.download_illust(illust_id, save_dir)

    def download_illusts(self, illust_ids, save_dir, bookmark_illust=False):
        """download illusts, aimed to fit indexer"""
        raise NotImplementedError


class PyxivIndexer:
    """
    Attrs:
        scope: search scope, in tag, or title and description, or in all
        mode: search mode, safe or r18 or both
        query: search match fuzzy or exactly
        include: whether use AND or OR to process query keywords
        order: result order by, always descending
    """
    # search scope
    S_TAG = 0
    S_TD = 1
    S_ALL = 2

    # search mode
    M_SAFE = 0
    M_R18 = 1
    M_ALL = 2

    # search
    Q_FUZZY = 0
    Q_EXACTLY = 1

    # include mode
    I_AND = 0
    I_OR = 1

    # order by
    O_LIKE = 0
    O_BOOKMARK = 1
    O_VIEW = 2

    def __init__(self, db_path):
        self.__scope = PyxivIndexer.S_TAG
        self.__mode = PyxivIndexer.M_SAFE
        self.__query = PyxivIndexer.Q_FUZZY
        self.__include = PyxivIndexer.I_AND
        self.__order = PyxivIndexer.O_LIKE
        self.db = PyxivDatabase(db_path)

    @property
    def scope(self):
        return self.__scope

    @scope.setter
    def scope(self, value):
        if value in (PyxivIndexer.S_TAG, PyxivIndexer.S_TD, PyxivIndexer.S_ALL):
            self.__scope = value
        else:
            raise ValueError("Unknown scope value: {}".format(value))

    @property
    def mode(self):
        return self.__mode

    @mode.setter
    def mode(self, value):
        if value in (PyxivIndexer.M_SAFE, PyxivIndexer.M_R18, PyxivIndexer.M_ALL):
            self.__mode = value
        else:
            raise ValueError("Unknown mode value: {}".format(value))

    @property
    def query(self):
        return self.__query

    @query.setter
    def query(self, value):
        if value in (PyxivIndexer.Q_FUZZY, PyxivIndexer.Q_EXACTLY):
            self.__query = value
        else:
            raise ValueError("Unknown query value: {}".format(value))

    @property
    def include(self):
        return self.__include

    @include.setter
    def include(self, value):
        if value in (PyxivIndexer.I_AND, PyxivIndexer.I_OR):
            self.__include = value
        else:
            raise ValueError("Unknown include value: {}".format(value))

    @property
    def order(self):
        return self.__order

    @order.setter
    def order(self, value):
        if value in (PyxivIndexer.O_LIKE, PyxivIndexer.O_BOOKMARK, PyxivIndexer.O_VIEW):
            self.__order = value
        else:
            raise ValueError("Unknown order value: {}".format(value))

    def search(self, includes: list) -> list:
        """search specified illusts

        Args:
            includes: a list includes texts you want to search

        Returns:
            A list consist of two-tuples, like (key, illust_id), where key is specified by order property
        """

        # fuzzy query
        if self.query == PyxivIndexer.Q_FUZZY:
            includes = ["%"+e+"%" for e in includes]

        o_value = {
            PyxivIndexer.O_LIKE: "like_count",
            PyxivIndexer.O_BOOKMARK: "bookmark_count",
            PyxivIndexer.O_VIEW: "view_count"
        }
        q_sql = {
            PyxivIndexer.Q_FUZZY: {
                "tag": " (name LIKE ?) ",
                "td": " (title LIKE ? OR description LIKE ?) "
            },
            PyxivIndexer.Q_EXACTLY: {
                "tag": " (name = ?) ",
                "td": " (title = ? OR description = ?) "
            }
        }

        sql_full = "SELECT id, {order} FROM illust;".format(order=o_value[self.order])
        sql_tag = "SELECT DISTINCT id, {order} FROM illust JOIN tag ON illust.id = tag.illust_id WHERE {where};".format(
            order=o_value[self.order],
            where=q_sql[self.query]["tag"])
        sql_td = "SELECT id, {order} FROM illust WHERE {where};".format(
            order=o_value[self.order],
            where=q_sql[self.query]["td"]
        )
        sql_r18 = "SELECT DISTINCT illust_id FROM tag WHERE name = 'R-18';"

        result_set = set(self.db(sql_full))
        if includes:
            # get tag and td sets
            tag_sets = []
            td_sets = []
            for name in includes:
                tag_sets.append(set(self.db(sql_tag, (name,))))
                td_sets.append(set(self.db(sql_td, (name, name))))
            tag_set = tag_sets[0].copy()
            td_set = td_sets[0].copy()

            # keywords AND or OR
            if self.include == PyxivIndexer.I_AND:
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
            if self.scope == PyxivIndexer.S_TAG:
                result_set.intersection_update(tag_set)
            elif self.scope == PyxivIndexer.S_TD:
                result_set.intersection_update(td_set)
            else:
                result_set.intersection_update(tag_set.union(td_set))

        result = sorted(result_set, key=lambda e: e[1], reverse=True)
        print(len(result))
        return result


if __name__ == "__main__":
    a = PyxivIndexer("./data/db/pyxiv.db")
    a.scope = PyxivIndexer.S_ALL
    a.mode = PyxivIndexer.M_ALL
    a.include = PyxivIndexer.I_OR
    (a.search(["azurlane", "アズールレーン"]))
