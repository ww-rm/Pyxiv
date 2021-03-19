import sqlite3
import requests
import wrapper
import json


class PyxivConfig:
    def __init__(self, config_path):
        self.__config = {}
        with open(config_path, "r", encoding="utf8") as f:
            self.__config = json.load(f)

    def __getattr__(self, name):
        return self.__config.get(name)


class PyxivBrowser:
    # lang=zh
    # 获取所有illust的id
    url_host = "https://www.pixiv.net"

    url_top_illust = "https://www.pixiv.net/ajax/top/illust"  # ?mode=all|r18 # many many info in index page

    url_search_tags = "https://www.pixiv.net/ajax/search/tags/{keyword}"
    # ?order=date&mode=all&p=1&s_mode=s_tag # param for url_search_*
    url_search_artworks = "https://www.pixiv.net/ajax/search/artworks/{keyword}"
    url_search_illustrations = "https://www.pixiv.net/ajax/search/illustrations/{keyword}"  # ?type=illust
    url_search_manga = "https://www.pixiv.net/ajax/search/manga/{keyword}"

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

    def __init__(self, proxies: dict = None, cookies: dict = None):
        self.session = requests.Session()
        self.session.headers = PyxivBrowser.headers
        if proxies:
            self.session.proxies = proxies
        if cookies:
            for name, value in cookies.items():
                self.session.cookies.set(name, value, domain=".pixiv.net", path="/")
        # print(self.session.cookies.list_domains())
        # print(self.session.proxies)
        # print(self.session.cookies)

    def __del__(self):
        self.session.close()

    @wrapper.browser_get
    def get_page(self, page_url) -> bytes:
        response = self.session.get(page_url)
        if response.status_code != requests.codes["ok"]:
            return b""
        return response.content

    @wrapper.cookies_required
    @wrapper.browser_get
    def get_top_illust(self, mode="all") -> dict:
        """Get top illusts by mode

        Args:
            mode: "all" means all ages, "r18" means R-18 only
        """
        json_ = self.session.get(PyxivBrowser.url_top_illust, params={"mode": mode}).json()
        return {} if json_.get("error") is True else json_.get("body")

    @wrapper.browser_get
    def get_search_artworks(self, keyword, order="date_d", mode="all", p=1, s_mode="s_tag", type_="all") -> dict:
        """Get search artworks result

        Args:
            order: "date" means date ascend, "date_d" means date descend
            mode: "all", "safe", "r18"
            p: search result page
            s_mode: "s_tag" partly match tag, "s_tag_full" exactly match tag, "s_tc" match title and character description
            type_: No need to care
        """
        json_ = self.session.get(
            PyxivBrowser.url_search_artworks.format(keyword=keyword),
            params={
                "order": order,
                "mode": mode,
                "p": p,
                "s_mode": s_mode,
                "type": type_
            }).json()
        return {} if json_.get("error") is True else json_.get("body")

    @wrapper.browser_get
    def get_search_illustrations(self, keyword, order="date_d", mode="all", p=1, s_mode="s_tag", type_="illust") -> dict:
        """Get search illustration or ugoira result

        Args:
            order: "date" means date ascend, "date_d" means date descend
            mode: "all", "safe", "r18"
            p: search result page
            s_mode: "s_tag" partly match tag, "s_tag_full" exactly match tag, "s_tc" match title and character description
            type_: "illust", "ugoira", "illust_and_ugoira"
        """
        json_ = self.session.get(
            PyxivBrowser.url_search_illustrations.format(keyword=keyword),
            params={
                "order": order,
                "mode": mode,
                "p": p,
                "s_mode": s_mode,
                "type": type_
            }).json()
        return {} if json_.get("error") is True else json_.get("body")

    @wrapper.browser_get
    def get_search_manga(self, keyword, order="date_d", mode="all", p=1, s_mode="s_tag", type_="manga") -> dict:
        """Get search manga result

        Args:
            order: "date" means date ascend, "date_d" means date descend
            mode: "all", "safe", "r18"
            p: search result page
            s_mode: "s_tag" partly match tag, "s_tag_full" exactly match tag, "s_tc" match title and character description
            type_: No need to care
        """
        json_ = self.session.get(
            PyxivBrowser.url_search_manga.format(keyword=keyword),
            params={
                "order": order,
                "mode": mode,
                "p": p,
                "s_mode": s_mode,
                "type": type_
            }).json()
        return {} if json_.get("error") is True else json_.get("body")

    @wrapper.browser_get
    def get_illust(self, illust_id) -> dict:
        json_ = self.session.get(PyxivBrowser.url_illust.format(illust_id=illust_id)).json()
        return {} if json_.get("error") is True else json_.get("body")

    @wrapper.browser_get
    def get_illust_pages(self, illust_id) -> list:
        json_ = self.session.get(PyxivBrowser.url_illust_pages.format(illust_id=illust_id)).json()
        return [] if json_.get("error") is True else json_.get("body")

    @wrapper.browser_get
    def get_user(self, user_id) -> dict:
        json_ = self.session.get(PyxivBrowser.url_user.format(user_id=user_id)).json()
        return {} if json_.get("error") is True else json_.get("body")

    @wrapper.cookies_required
    @wrapper.browser_get
    def get_user_following(self, user_id, offset, limit=50, rest="show") -> dict:
        """Get following list of a user

        Args:
            offset: Start index of list
            limit: Number of list, default to "50", must < 90
            rest(restrict): "show" means "public", "hide" means private, you can just see private followings for your own account

        Returns:
            The list is body.users
        """
        json_ = self.session.get(
            PyxivBrowser.url_user_following.format(user_id=user_id),
            params={"offset": offset, "limit": limit if limit < 90 else 90, "rest": rest}
        ).json()
        return {} if json_.get("error") is True else json_.get("body")

    @wrapper.cookies_required
    @wrapper.browser_get
    def get_user_recommends(self, user_id, userNum=100, workNum=3, isR18=True) -> dict:
        """Get recommends of a user

        Args:
            userNum: Number of recommends' user, limit to less than 100
            workNum: Unknown
            isR18: Unknown

        Returns:
            Recommends list is body.recommendUsers, the length of list <= userNum
        """
        json_ = self.session.get(
            PyxivBrowser.url_user_recommends.format(user_id=user_id),
            params={"userNum": userNum, "workNum": workNum, "isR18": isR18}
        ).json()
        return {} if json_.get("error") is True else json_.get("body")

    @wrapper.browser_get
    def get_user_profile_all(self, user_id) -> dict:
        json_ = self.session.get(PyxivBrowser.url_user_profile_all.format(user_id=user_id)).json()
        return {} if json_.get("error") is True else json_.get("body")

    @wrapper.browser_get
    def get_user_profile_top(self, user_id) -> dict:
        json_ = self.session.get(PyxivBrowser.url_user_profile_top.format(user_id=user_id)).json()
        return {} if json_.get("error") is True else json_.get("body")


class PyxivDatabase:
    """PyxivDatabase

    Tables:
        CREATE TABLE "user" (
            "id" INTEGER NOT NULL ON CONFLICT REPLACE DEFAULT 0,
            "name" TEXT NOT NULL ON CONFLICT REPLACE DEFAULT '' COLLATE NOCASE,
            PRIMARY KEY ("id") ON CONFLICT REPLACE
        );
        CREATE TABLE "illust" (
            "id" INTEGER NOT NULL ON CONFLICT REPLACE DEFAULT 0,
            "title" TEXT NOT NULL ON CONFLICT REPLACE DEFAULT '' COLLATE NOCASE,
            "description" TEXT NOT NULL ON CONFLICT REPLACE DEFAULT '' COLLATE NOCASE,
            "bookmark_count" integer NOT NULL ON CONFLICT REPLACE DEFAULT 0,
            "like_count" integer NOT NULL ON CONFLICT REPLACE DEFAULT 0,
            "view_count" integer NOT NULL ON CONFLICT REPLACE DEFAULT 0,
            "user_id" integer NOT NULL ON CONFLICT REPLACE DEFAULT 0,
            PRIMARY KEY ("id") ON CONFLICT REPLACE,
            FOREIGN KEY ("user_id") REFERENCES "user" ("id") ON DELETE CASCADE ON UPDATE CASCADE
        );
        CREATE TABLE "page" (
            "illust_id" INTEGER NOT NULL ON CONFLICT REPLACE DEFAULT 0,
            "page_id" INTEGER NOT NULL ON CONFLICT REPLACE DEFAULT 0,
            "url_original" TEXT NOT NULL ON CONFLICT REPLACE DEFAULT '' COLLATE NOCASE,
            PRIMARY KEY ("illust_id", "page_id") ON CONFLICT REPLACE,
            FOREIGN KEY ("illust_id") REFERENCES "illust" ("id") ON DELETE CASCADE ON UPDATE CASCADE
        );
        CREATE TABLE "tag" (
            "name" TEXT NOT NULL ON CONFLICT REPLACE DEFAULT '' COLLATE NOCASE,
            "illust_id" INTEGER NOT NULL ON CONFLICT REPLACE DEFAULT 0,
            PRIMARY KEY ("name", "illust_id") ON CONFLICT REPLACE,
            FOREIGN KEY ("illust_id") REFERENCES "illust" ("id") ON DELETE CASCADE ON UPDATE CASCADE
        );

    Methods:
        insert_*: insert or update row
    """

    def __init__(self, db_path):
        self.connection = sqlite3.connect(db_path, isolation_level=None)
        self._init()

    def __del__(self):
        self.connection.close()

    @wrapper.database_operation
    def __call__(self, sql: str, parameters=None) -> list:
        """A shortcut method for "execute" method to execute sql commands

        Returns:
            Always returns the fetchall() of a cursor object
        """
        if parameters:
            return self.connection.execute(sql, parameters).fetchall()
        else:
            return self.connection.execute(sql).fetchall()

    def _init(self):
        cursor = self.connection.execute("SELECT name FROM sqlite_master WHERE type='table';")
        if not cursor.fetchall():
            self.connection.execute(
                """CREATE TABLE "user" (
                    "id" INTEGER NOT NULL ON CONFLICT REPLACE DEFAULT 0,
                    "name" TEXT NOT NULL ON CONFLICT REPLACE DEFAULT '' COLLATE NOCASE,
                    PRIMARY KEY ("id") ON CONFLICT REPLACE
                );"""
            )
            self.connection.execute(
                """CREATE TABLE "illust" (
                    "id" INTEGER NOT NULL ON CONFLICT REPLACE DEFAULT 0,
                    "title" TEXT NOT NULL ON CONFLICT REPLACE DEFAULT '' COLLATE NOCASE,
                    "description" TEXT NOT NULL ON CONFLICT REPLACE DEFAULT '' COLLATE NOCASE,
                    "bookmark_count" integer NOT NULL ON CONFLICT REPLACE DEFAULT 0,
                    "like_count" integer NOT NULL ON CONFLICT REPLACE DEFAULT 0,
                    "view_count" integer NOT NULL ON CONFLICT REPLACE DEFAULT 0,
                    "user_id" integer NOT NULL ON CONFLICT REPLACE DEFAULT 0,
                    PRIMARY KEY ("id") ON CONFLICT REPLACE,
                    FOREIGN KEY ("user_id") REFERENCES "user" ("id") ON DELETE CASCADE ON UPDATE CASCADE
                );"""
            )
            self.connection.execute(
                """CREATE TABLE "page" (
                    "illust_id" INTEGER NOT NULL ON CONFLICT REPLACE DEFAULT 0,
                    "page_id" INTEGER NOT NULL ON CONFLICT REPLACE DEFAULT 0,
                    "url_original" TEXT NOT NULL ON CONFLICT REPLACE DEFAULT '' COLLATE NOCASE,
                    PRIMARY KEY ("illust_id", "page_id") ON CONFLICT REPLACE,
                    FOREIGN KEY ("illust_id") REFERENCES "illust" ("id") ON DELETE CASCADE ON UPDATE CASCADE
                );"""
            )
            self.connection.execute(
                """CREATE TABLE "tag" (
                    "name" TEXT NOT NULL ON CONFLICT REPLACE DEFAULT '' COLLATE NOCASE,
                    "illust_id" INTEGER NOT NULL ON CONFLICT REPLACE DEFAULT 0,
                    PRIMARY KEY ("name", "illust_id") ON CONFLICT REPLACE,
                    FOREIGN KEY ("illust_id") REFERENCES "illust" ("id") ON DELETE CASCADE ON UPDATE CASCADE
                );"""
            )

    @wrapper.database_operation
    def insert_user(self, id_, name):
        self.connection.execute(
            "INSERT INTO user VALUES (?, ?);",
            (id_, name)
        )

    @wrapper.database_operation
    def insert_illust(self, id_, title, description, bookmark_count, like_count, view_count, user_id):
        self.connection.execute(
            "INSERT INTO illust VALUES (?, ?, ?, ?, ?, ?, ?);",
            (id_, title, description, bookmark_count, like_count, view_count, user_id)
        )

    @wrapper.database_operation
    def insert_page(self, illust_id, page_id, url_original):
        self.connection.execute(
            "INSERT INTO page VALUES (?, ?, ?);",
            (illust_id, page_id, url_original)
        )

    @wrapper.database_operation
    def insert_tag(self, name, illust_id):
        self.connection.execute(
            "INSERT INTO tag VALUES (?, ?);",
            (name, illust_id)
        )
