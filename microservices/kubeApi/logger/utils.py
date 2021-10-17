import time
from fastapi.logger import logger
from functools import wraps


def timeit(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        logger.debug("Function %s executed in %f s", func.__name__, end - start)
        return result
    return wrapper
