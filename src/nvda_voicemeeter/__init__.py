import subprocess as sp

from .cdll import NVDA_PATH
from .window import request_window_object as draw


def launch():
    if NVDA_PATH:
        sp.Popen([NVDA_PATH], shell=True)


__ALL__ = ["launch", "draw"]
