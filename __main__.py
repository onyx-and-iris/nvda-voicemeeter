import logging

import voicemeeterlib

import nvda_voicemeeter

logging.basicConfig(level=logging.DEBUG)

nvda_voicemeeter.launch()

KIND_ID = "potato"

with voicemeeterlib.api(KIND_ID) as vm:
    with nvda_voicemeeter.draw(f"Voicemeeter {KIND_ID.capitalize()} NVDA", vm) as window:
        window.run()
