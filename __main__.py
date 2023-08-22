import logging

import voicemeeterlib

import nvda_voicemeeter

logging.basicConfig(level=logging.DEBUG)

kind_id = "potato"

with voicemeeterlib.api(kind_id) as vm:
    with nvda_voicemeeter.build(f"Voicemeeter {kind_id.capitalize()} NVDA", vm) as window:
        window.run()
