import voicemeeterlib

import nvda_voicemeeter

KIND_ID = "potato"

with voicemeeterlib.api(KIND_ID) as vm:
    with nvda_voicemeeter.draw(KIND_ID, vm) as window:
        window.run()
