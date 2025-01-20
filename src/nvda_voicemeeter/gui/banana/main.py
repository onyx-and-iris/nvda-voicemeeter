import voicemeeterlib

import nvda_voicemeeter


def run():
    KIND_ID = 'banana'

    with voicemeeterlib.api(KIND_ID) as vm:
        with nvda_voicemeeter.draw(KIND_ID, vm) as window:
            window.run()
