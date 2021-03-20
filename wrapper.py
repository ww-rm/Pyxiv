import random
from functools import wraps
from time import sleep
import sys
import sqlite3


def browser_get(method, log_file=sys.stderr, max_sleep_seconds=3):
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
            print("Empty Return:{}:{}:{}".format(method.__name__, args, kwargs), file=log_file)
        return ret
    return decorated_method

def browser_post(method, log_file=sys.stderr, max_sleep_seconds=3):
    @wraps(method)
    def decorated_method(self, *args, **kwargs):
        sleep(0.1+random.random()*(max_sleep_seconds-0.1))
        try:
            method(self, *args, **kwargs)
        except Exception as e:
            print(e.__class__, e, file=log_file)
    return decorated_method


def cookies_required(method):
    """Raise PermissionError when cookies not found."""
    @wraps(method)
    def decorated_method(self, *args, **kwargs):
        if not (
            self.session.cookies.get("PHPSESSID", domain=".pixiv.net", path="/") and
            self.session.cookies.get("device_token", domain=".pixiv.net", path="/") and
            self.session.cookies.get("privacy_policy_agreement", domain=".pixiv.net", path="/")
        ):
            raise PermissionError("Cookies not found!")
        else:
            return method(self, *args, **kwargs)
    return decorated_method


def log_calling_info(method, log_file=sys.stdout):
    """Log method calling info."""
    @wraps(method)
    def decorated_method(self, *args, **kwargs):
        info_msg = "Calling Func:{}:{}:{}".format(method.__name__, args, kwargs)
        print(info_msg, file=log_file)
        return method(self, *args, **kwargs)
    return decorated_method


def database_operation(method, log_file=sys.stderr):
    @wraps(method)
    def decorated_method(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except sqlite3.Error as e:
            print(e.__class__, e, file=log_file)
            print("Failed to Execute:{}:{}:{}".format(method.__name__, args, kwargs), file=log_file)
            return []
    return decorated_method
