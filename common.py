import time
from datetime import datetime as dt
from html import unescape


def limit_rate(number_of_calls: int, in_time: int):
    """A simple rate limiter.

    The algorithm used here is fine for the purpose of this script. In general, it can be not so great idea.

    All the times of called are stored in an internal list.
    For each call, we check the value at the position `[-number_of_calls]`.

    If the number stored + `in_time` is bigger than `now`.

    If it's smaller, then all is fine, now is appended to the list,
    and the function is called.

    If it's bigger, then we need to wait for `[-number_of_calls] + in_time - now`.

    This is a decorator, so should be used with:

        @limit_rate(number_of_calls=10, in_time=3600)
        def func():
            pass

    :param number_of_calls: number of calls that are allowed in the amount of time
    :param in_time: number of seconds
    """

    # duration of one function call in ms
    print(f"Requested {number_of_calls} function calls in {in_time}s")

    def decorator(func):
        called_times = []

        def wrapper(*args, **kwargs):
            now = dt.utcnow().timestamp()

            if len(called_times) >= number_of_calls:
                called_x_times_before = called_times[-number_of_calls]
                need_delay = called_x_times_before + in_time - now
                if need_delay > 0:
                    print(f"sleeping for {int(need_delay)}s")
                    time.sleep(need_delay)

            called_times.append(dt.utcnow().timestamp())

            ret = func(*args, **kwargs)
            return ret

        return wrapper

    return decorator


def convert(data):
    return unescape(data) if data != None else None
