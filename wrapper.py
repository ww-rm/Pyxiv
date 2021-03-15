import random
from functools import wraps
from time import sleep
import sys


def randsleep(method, max_seconds=5):
    """Randomly sleep seconds before calling wrapped function."""
    @wraps(method)
    def decorated_method(self, *args, **kwargs):
        sleep(0.1+random.random()*(max_seconds-0.1))
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


def log_empty_return(method, log_file=sys.stderr, raise_runtime_error=False):
    """Check if wrapped function returned empty value."""
    @wraps(method)
    def decorated_method(self, *args, **kwargs):
        ret = method(self, *args, **kwargs)
        if not ret:
            error_msg = "Empty Return:Method:{}:Args:{}:KwArgs:{}".format(method.__name__, args, kwargs)
            if raise_runtime_error:
                raise RuntimeError(error_msg)
            else:
                print(error_msg, file=log_file)
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
