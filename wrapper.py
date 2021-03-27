import random
import sqlite3
import sys
from functools import wraps
from time import sleep


def browser_get(log_file=sys.stderr, max_sleep_seconds=1):
    def decorator(method):
        @wraps(method)
        def decorated_method(self, *args, **kwargs):
            sleep(0.1+random.random()*(max_sleep_seconds-0.1))
            ret = None
            try:
                ret = method(self, *args, **kwargs)
            except Exception as e:
                print(e.__class__, e, file=log_file)
            if not ret:
                ret = None
                print("Empty Get:{}:{}:{}".format(method.__name__, args, kwargs), file=log_file)
            return ret
        return decorated_method
    return decorator


def browser_post(log_file=sys.stderr, max_sleep_seconds=1):
    def decorator(method):
        @wraps(method)
        def decorated_method(self, *args, **kwargs):
            ret_code = False
            sleep(0.1+random.random()*(max_sleep_seconds-0.1))
            try:
                ret_code = method(self, *args, **kwargs)
            except Exception as e:
                print(e.__class__, e, file=log_file)
            if not ret_code:
                print("Failed Post:{}:{}:{}".format(method.__name__, args, kwargs), file=log_file)
            return ret_code
        return decorated_method
    return decorator


def cookies_required():
    """Raise PermissionError when cookies not found."""
    def decorator(method):
        @wraps(method)
        def decorated_method(self, *args, **kwargs):
            if not self.session.cookies.get("PHPSESSID", domain=".pixiv.net", path="/"):
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


def database_operation(log_file=sys.stderr):
    def decorator(method):
        @wraps(method)
        def decorated_method(self, *args, **kwargs):
            try:
                return method(self, *args, **kwargs)
            except sqlite3.Error as e:
                print(e.__class__, e, file=log_file)
                print("Failed to Execute:{}:{}:{}".format(method.__name__, args, kwargs), file=log_file)
                return []
        return decorated_method
    return decorator
