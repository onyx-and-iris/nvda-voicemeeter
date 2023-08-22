import voicemeeterlib

import nvda_voicemeeter

kind_id = "potato"

with voicemeeterlib.api("potato") as vm:
    with nvda_voicemeeter.build(f"Voicemeeter {kind_id.capitalize()} NVDA", vm) as window:
        window.run()
