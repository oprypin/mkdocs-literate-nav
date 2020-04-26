import functools


def collect(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        return list(f(*args, **kwargs))

    return wrapped
