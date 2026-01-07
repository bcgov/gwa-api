from functools import wraps
import logging
import sys
import asyncio
from typing import Callable, Any, Optional


def log_entry_exit(logger: Optional[logging.Logger] = None) -> Callable:
    """
    Decorator that logs function entry/exit for both sync and async functions.
    
    Args:
        logger: Optional logger instance to use.
                If None, uses a logger named after the current module (__name__).
    """
    # Default to module-level logger if none provided
    if logger is None:
        logger = logging.getLogger(__name__)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            func_name = func.__name__
            logger.info(f"<{func_name}")

            try:
                result = await func(*args, **kwargs)
                logger.info(f">{func_name} {result}")
                return result

            except Exception:
                exc_type = type(sys.exception()).__name__
                logger.error(f">{func_name} with exception: {exc_type}")
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            func_name = func.__name__
            logger.info(f"<{func_name}")

            try:
                result = func(*args, **kwargs)
                logger.info(f">{func_name} {result}")
                return result

            except Exception:
                exc_type = type(sys.exception()).__name__
                logger.error(f">{func_name} with exception: {exc_type}")
                raise

        # Choose appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator