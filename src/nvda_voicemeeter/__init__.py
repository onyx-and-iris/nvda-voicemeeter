import subprocess as sp
import time

from .cdll import NVDA_PATH
from .window import request_window_object as draw


def launch(delay=1):
    if NVDA_PATH:
        sp.Popen([NVDA_PATH], shell=True)
        time.sleep(delay)


__ALL__ = ["launch", "draw"]
