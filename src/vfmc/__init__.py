import functools
import logging


def catch_errors(func):
    """
    Untrapped errors in PyQt event handlers can cause crashes
    They should use this decorator to catch and log errors
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Log the actual exception that was raised
            logging.exception(f"Error in event handler {func.__name__}: {str(e)}")
            return None

    return wrapper


def catch_and_return(return_value=None):
    """
    Similar to above, but specify a valid return value when an exception is caught
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Log the actual exception that was raised
                logging.exception(f"Error in event handler {func.__name__}: {str(e)}")
                return return_value

        return wrapper

    return decorator
