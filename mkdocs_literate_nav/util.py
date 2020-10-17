import functools
from typing import Callable, Iterable, List, TypeVar

T = TypeVar("T")


def collect(f: Callable[..., Iterable[T]]) -> Callable[..., List[T]]:
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        return list(f(*args, **kwargs))

    return wrapped
