import sqlite3
import requests
import wrapper


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

    def __init__(self, proxies=None, cookies=None):
        self.session = requests.Session()
        self.session.headers = PyxivBrowser.headers
        if proxies:
            self.session.proxies = proxies
        if cookies:
            self.session.cookies.update(cookies)
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
    def get_top_illust(self, mode="all"):
        """Get top illusts by mode

        Args:
            mode: "all" means all ages, "r18" means R-18 only
        """
        json_ = self.session.get(PyxivBrowser.url_top_illust, params={"mode": mode}).json()
        return {} if json_.get("error") is True else json_.get("body")

    @wrapper.browser_get
    def get_search_artworks(self, keyword, order="date_d", mode="all", p=1, s_mode="s_tag", type_="all"):
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
    def get_search_illustrations(self, keyword, order="date_d", mode="all", p=1, s_mode="s_tag", type_="illust"):
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
    def get_search_manga(self, keyword, order="date_d", mode="all", p=1, s_mode="s_tag", type_="manga"):
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
    def get_illust(self, illust_id):
        json_ = self.session.get(PyxivBrowser.url_illust.format(illust_id=illust_id)).json()
        return {} if json_.get("error") is True else json_.get("body")

    @wrapper.browser_get
    def get_illust_pages(self, illust_id):
        json_ = self.session.get(PyxivBrowser.url_illust_pages.format(illust_id=illust_id)).json()
        return {} if json_.get("error") is True else json_.get("body")

    @wrapper.browser_get
    def get_user(self, user_id):
        json_ = self.session.get(PyxivBrowser.url_user.format(user_id=user_id)).json()
        return {} if json_.get("error") is True else json_.get("body")

    @wrapper.cookies_required
    @wrapper.browser_get
    def get_user_following(self, user_id, offset, limit=50, rest="show"):
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
    def get_user_recommends(self, user_id, userNum, workNum=3, isR18=True):
        """Get recommends of a user

        Args:
            userNum: Number of recommends' user
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
    def get_user_profile_all(self, user_id):
        json_ = self.session.get(PyxivBrowser.url_user_profile_all.format(user_id=user_id)).json()
        return {} if json_.get("error") is True else json_.get("body")

    @wrapper.browser_get
    def get_user_profile_top(self, user_id):
        json_ = self.session.get(PyxivBrowser.url_user_profile_top.format(user_id=user_id)).json()
        return {} if json_.get("error") is True else json_.get("body")


class PyxivDatabase:
    """PyxivDatabase

    Tables:
        "user" (
            "id" INTEGER NOT NULL DEFAULT 0,
            "name" TEXT NOT NULL DEFAULT '',
            PRIMARY KEY ("id")
        )
        "illust" (
            "id" INTEGER NOT NULL DEFAULT 0,
            "user_id" INTEGER NOT NULL DEFAULT 0,
            "title" TEXT NOT NULL DEFAULT '',
            PRIMARY KEY ("id"),
            FOREIGN KEY ("user_id") REFERENCES "user" ("id") ON DELETE CASCADE ON UPDATE CASCADE
        )
        "page" (
            "illust_id" INTEGER NOT NULL DEFAULT 0,
            "page_id" INTEGER NOT NULL DEFAULT 0,
            "url_original" TEXT NOT NULL DEFAULT '',
            "save_path" TEXT NOT NULL DEFAULT '',
            PRIMARY KEY ("illust_id", "page_id"),
            FOREIGN KEY ("illust_id") REFERENCES "illust" ("id") ON DELETE CASCADE ON UPDATE CASCADE
        )
        "tag" (
            "name" TEXT NOT NULL DEFAULT '',
            "illust_id" INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY ("name", "illust_id"),
            FOREIGN KEY ("illust_id") REFERENCES "illust" ("id") ON DELETE CASCADE ON UPDATE CASCADE
        )
    """

    tables = ["user", "illust", "page", "tag"]
    fields = {
        "user": ["id", "name"],
        "illust": ["id", "user_id", "title"],
        "page": ["illust_id", "page_id", "url_original", "save_path"],
        "tag": ["name", "illust_id"]
    }

    def __init__(self, db_path):
        self.connection = sqlite3.connect(db_path, isolation_level=None)
        self._init()

    def __del__(self):
        self.connection.close()

    def _init(self):
        cursor = self.connection.execute("SELECT name FROM sqlite_master WHERE type='table';")
        if not cursor.fetchall():
            self.connection.execute(
                """CREATE TABLE "user" (
                    "id" INTEGER NOT NULL DEFAULT 0,
                    "name" TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY ("id")
                );"""
            )
            self.connection.execute(
                """CREATE TABLE "illust" (
                    "id" INTEGER NOT NULL DEFAULT 0,
                    "user_id" INTEGER NOT NULL DEFAULT 0,
                    "title" TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY ("id"),
                    FOREIGN KEY ("user_id") REFERENCES "user" ("id") ON DELETE CASCADE ON UPDATE CASCADE
                );"""
            )
            self.connection.execute(
                """CREATE TABLE "page" (
                    "illust_id" INTEGER NOT NULL DEFAULT 0,
                    "page_id" INTEGER NOT NULL DEFAULT 0,
                    "url_original" TEXT NOT NULL DEFAULT '',
                    "save_path" TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY ("illust_id", "page_id"),
                    FOREIGN KEY ("illust_id") REFERENCES "illust" ("id") ON DELETE CASCADE ON UPDATE CASCADE
                );"""
            )
            self.connection.execute(
                """CREATE TABLE "tag" (
                    "name" TEXT NOT NULL DEFAULT '',
                    "illust_id" INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY ("name", "illust_id"),
                    FOREIGN KEY ("illust_id") REFERENCES "illust" ("id") ON DELETE CASCADE ON UPDATE CASCADE
                );"""
            )

    @wrapper.database_operation
    def insert_user(self, id_, name):
        self.connection.execute("INSERT INTO user VALUES (?, ?);", (id_, name))

    @wrapper.database_operation
    def insert_illust(self, id_, user_id, title):
        self.connection.execute("INSERT INTO illust VALUES (?, ?, ?);", (id_, user_id, title))

    @wrapper.database_operation
    def insert_page(self, illust_id, page_id, url_original, save_path=""):
        self.connection.executemany("INSERT INTO page VALUES (?, ?, ?, ?);", (illust_id, page_id, url_original, save_path))

    @wrapper.database_operation
    def insert_tag(self, name, illust_id):
        self.connection.execute("INSERT INTO tag VALUES (?, ?);", (name, illust_id))

    @wrapper.database_operation
    def update_page_save_path(self, illust_id, page_id, save_path=""):
        self.connection.executemany(
            "UPDATE page SET save_path = ? WHERE illust_id = ? AND page_id = ?;",
            (save_path, illust_id, page_id)
        )

    # get save_path

    @wrapper.database_operation
    def select_page_save_path_by_tag(self, names):
        results = []
        for name in names:
            cursor = self.connection.execute(
                """SELECT save_path FROM page
                    WHERE illust_id = (
                        SELECT DISTINCT illust_id FROM tag
                        WHERE tag = ?
                    )""", (name,)
            )
            results.append(cursor.fetchall())

        result = set(results[0])
        for r in results[1:]:
            result.intersection_update(r)
        return list(result)

    @wrapper.database_operation
    def select_page_save_path_by_user_name(self, name):
        cursor = self.connection.execute(
            """SELECT save_path FROM page
                WHERE illust_id = (
                    SELECT id FROM illust
                    WHERE user_id = (SELECT id FROM user WHERE name = ?)
                )""", (name,)
        )
        return cursor.fetchall()

    @wrapper.database_operation
    def select_page_save_path_by_user_id(self, id_):
        cursor = self.connection.execute(
            """SELECT save_path FROM page
                WHERE illust_id = (SELECT id FROM illust WHERE user_id = ?)""", (id_,)
        )
        return cursor.fetchall()

    @wrapper.database_operation
    def select_page_save_path_by_illust_id(self, id_):
        cursor = self.connection.execute("SELECT save_path FROM page WHERE illust_id = ?", (id_,))
        return cursor.fetchall()

    # get url_original
    # return (user.id, user.name, illust.id, page.url_original)

    @wrapper.database_operation
    def select_page_url_original_by_tag(self, names):
        """return (user.id, user.name, illust.id, page.url_original)"""
        results = []
        for name in names:
            cursor = self.connection.execute(
                """SELECT user.id, user.name, illust.id, url_original FROM user JOIN illust JOIN page JOIN tag
                    WHERE illust.id = (
                        SELECT DISTINCT illust_id FROM tag
                        WHERE tag = ?
                    ) AND save_path != ''""", (name,)
            )
            results.append(cursor.fetchall())

        result = set(results[0])
        for r in results[1:]:
            result.intersection_update(r)
        return list(result)

    @wrapper.database_operation
    def select_page_url_original_by_user_name(self, name):
        """return (user.id, user.name, illust.id, page.url_original)"""
        cursor = self.connection.execute(
            """SELECT user.id, user.name, illust.id, url_original FROM user JOIN illust JOIN page JOIN tag
                WHERE illust.id = (
                    SELECT id FROM illust
                    WHERE user_id = (SELECT id FROM user WHERE name = ?)
                ) AND save_path != ''""", (name,)
        )
        return cursor.fetchall()

    @wrapper.database_operation
    def select_page_url_original_by_user_id(self, id_):
        """return (user.id, user.name, illust.id, page.url_original)"""
        cursor = self.connection.execute(
            """SELECT user.id, user.name, illust.id, url_original FROM user JOIN illust JOIN page JOIN tag
                WHERE illust.id = (SELECT id FROM illust WHERE user_id = ?) AND save_path != ''""", (id_,)
        )
        return cursor.fetchall()

    @wrapper.database_operation
    def select_page_url_original_by_illust_id(self, id_):
        """return (user.id, user.name, illust.id, page.url_original)"""
        cursor = self.connection.execute(
            """SELECT user.id, user.name, illust.id, url_original FROM user JOIN illust JOIN page JOIN tag 
                WHERE illust.id = ? AND save_path != ''""",
            (id_,)
        )
        return cursor.fetchall()

    # list values

    def list_tag_name(self):
        cursor = self.connection.execute("SELECT DISTINCT name FROM tag")
        return cursor.fetchall()

    def list_user_id_name(self):
        cursor = self.connection.execute("SELECT id, name, FROM user")
        return cursor.fetchall()

    def list_illust_title(self):
        cursor = self.connection.execute("SELECT title FROM illust")
        return cursor.fetchall()
