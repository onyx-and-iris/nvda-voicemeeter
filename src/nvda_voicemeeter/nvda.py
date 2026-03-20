from enum import IntEnum

from .cdll import libc
from .errors import NVDAVMCAPIError


class ServerState(IntEnum):
    RUNNING = 0
    UNAVAILABLE = 1722


class CBindings:
    bind_test_if_running = libc.nvdaController_testIfRunning
    bind_speak_text = libc.nvdaController_speakText
    bind_cancel_speech = libc.nvdaController_cancelSpeech
    bind_braille_message = libc.nvdaController_brailleMessage

    def _call(self, fn, *args, ok=(0,)) -> int:
        retval = fn(*args)
        if retval not in ok:
            raise NVDAVMCAPIError(fn.__name__, retval)
        return retval

    def test_if_running(self) -> int:
        return self._call(self.bind_test_if_running, ok=(ServerState.RUNNING, ServerState.UNAVAILABLE))

    def speak_text(self, text: str) -> None:
        self._call(self.bind_speak_text, text)

    def cancel_speech(self) -> None:
        self._call(self.bind_cancel_speech)

    def braille_message(self, text: str) -> None:
        self._call(self.bind_braille_message, text)


class Nvda:
    def __init__(self):
        self._bindings = CBindings()

    @property
    def is_running(self) -> bool:
        return self._bindings.test_if_running() == ServerState.RUNNING

    def speak(self, text: str) -> None:
        self._bindings.speak_text(text)

    def cancel_speech(self) -> None:
        self._bindings.cancel_speech()

    def braille_message(self, text: str) -> None:
        self._bindings.braille_message(text)
