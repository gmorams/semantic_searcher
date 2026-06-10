import time
import functools


class SingletonMeta(type):
    """Metaclasse Singleton per assegurar una sola instància per classe."""
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


def measure_time(func):
    """Decorator que mesura i imprimeix el temps d'execució d'una funció."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"[{func.__qualname__}] {elapsed:.2f}s")
        return result
    return wrapper
