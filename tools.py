# import numpy as np


# should go to `tools.py`
def coroutine(func):
    """ decorator that auto-initializes (calls `next(None)`) coroutines"""
    def start(*args, **kwargs):
        cr = func(*args, **kwargs)
        cr.next()
        return cr
    return start


# read ctrl file - this should also work for log files
# ctrl = np.genfromtxt('wn.txt', dtype=None, names=True, delimiter='\t')

# writing a nicely formatted log file seems more complicated
