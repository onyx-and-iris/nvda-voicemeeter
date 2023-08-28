import logging

import voicemeeterlib

import nvda_voicemeeter

logging.basicConfig(level=logging.DEBUG)

KIND_ID = "potato"

with voicemeeterlib.api(KIND_ID, sync=True) as vm:
    with nvda_voicemeeter.draw(KIND_ID, vm) as window:
        window.run()
