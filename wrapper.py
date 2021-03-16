import random
from functools import wraps
from time import sleep
import sys


def browser_get(method, log_file=sys.stderr, max_sleep_seconds=5):
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
            print("Empty Return:{}:{}:{}".format(method.__name__, args, kwargs))
        return ret
    return decorated_method


def cookies_required(method):
    """Raise PermissionError when cookies not found."""
    @wraps(method)
    def decorated_method(self, *args, **kwargs):
        if not (
            "PHPSESSID" in self.session.cookies and
            "device_token" in self.session.cookies and
            "privacy_policy_agreement" in self.session.cookies
        ):
            raise PermissionError("Cookies not found!")
        else:
            return method(self, *args, **kwargs)
    return decorated_method


def log_setter_error(method, log_file=sys.stderr):
    """Check if failed to set property."""
    @wraps(method)
    def decorated_method(self, *args, **kwargs):
        try:
            method(self, *args, **kwargs)
        except Exception as e:
            error_msg = "Failed to Set:Property:{}".format(method.__name__)
            print(error_msg, file=log_file)
    return decorated_method


def log_calling_info(method, log_file=sys.stdout):
    """Log method calling info."""
    @wraps(method)
    def decorated_method(self, *args, **kwargs):
        info_msg = "Calling Func:Method:{}:Args:{}:KwArgs:{}".format(method.__name__, args, kwargs)
        print(info_msg, file=log_file)
        return method(self, *args, **kwargs)
    return decorated_method
