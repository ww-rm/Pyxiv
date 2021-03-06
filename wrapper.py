import logging
import sqlite3
import sys
from functools import wraps
from time import sleep
from urllib.parse import urlparse, urlunparse
import warnings
from urllib3.exceptions import InsecureRequestWarning


def requests_alter(alter_dict: dict = None):
    """Change domain of a request with alter_dict mapping {"domain": "ip"}
    """
    alter_dict = alter_dict or {
        "pixiv.net": "210.140.131.218",
        "www.pixiv.net": "210.140.131.218",
        "i.pximg.net": "210.140.92.142",
    }

    def decorator(func):
        @wraps(func)
        def decorated_func(self, method, url, *args, **kwargs):
            _url = urlparse(url)
            if _url.netloc in alter_dict:
                url = urlunparse((
                    _url.scheme, alter_dict.get(_url.netloc, _url.netloc),
                    _url.path, _url.params, _url.query, _url.fragment
                ))
                kwargs["headers"] = kwargs.get("headers", {})
                kwargs["headers"]["Host"] = _url.netloc
                kwargs["verify"] = False
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", InsecureRequestWarning)
                return func(self, method, url, *args, **kwargs)
        return decorated_func
    return decorator


def empty_retry(times=3, interval=1):
    """Retry when a func returns empty

    Args

    times:
        how many times to retry
    interval:
        interval between each retry, in seconds
    """
    def decorator(func):
        @wraps(func)
        def decorated_func(*args, **kwargs):
            for _ in range(times):
                ret = func(*args, **kwargs)
                if ret:
                    return ret
                sleep(interval)
            logging.getLogger(__name__).error("All retries failed in func {}.".format(func.__name__))
            return ret
        return decorated_func
    return decorator


def cookies_required():
    """Raise PermissionError when cookies not found."""
    def decorator(method):
        @wraps(method)
        def decorated_method(self, *args, **kwargs):
            if not self.cookies.get("PHPSESSID", domain=".pixiv.net", path="/"):
                raise PermissionError("Cookies not found!")
            else:
                return method(self, *args, **kwargs)
        return decorated_method
    return decorator


def log_calling_info(log_file=sys.stdout):
    """Log method calling info."""
    def decorator(method):
        @wraps(method)
        def decorated_method(self, *args, **kwargs):
            info_msg = "Calling Func:{}:{}:{}".format(method.__name__, args, kwargs)
            print(info_msg, file=log_file)
            return method(self, *args, **kwargs)
        return decorated_method
    return decorator


def database_operation():
    def decorator(method):
        @wraps(method)
        def decorated_method(self, *args, **kwargs):
            try:
                return method(self, *args, **kwargs)
            except sqlite3.Error as e:
                logging.getLogger(__name__).error("Failed to Execute:{}:{}:{}".format(method.__name__, args, kwargs))
                return []
        return decorated_method
    return decorator
