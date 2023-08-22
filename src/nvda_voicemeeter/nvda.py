from .cdll import libc
from .errors import NVDAVMCAPIError


class CBindings:
    bind_test_if_running = libc.nvdaController_testIfRunning
    bind_speak_text = libc.nvdaController_speakText
    bind_cancel_speech = libc.nvdaController_cancelSpeech
    bind_braille_message = libc.nvdaController_brailleMessage

    def call(self, fn, *args, ok=(0,), ok_exp=None):
        retval = fn(*args)
        if ok_exp is None:
            if retval not in ok:
                raise NVDAVMCAPIError(fn.__name__, retval)
        elif not ok_exp(retval) and retval not in ok:
            raise NVDAVMCAPIError(fn.__name__, retval)
        return retval


class Nvda(CBindings):
    @property
    def is_running(self):
        return self.call(self.bind_test_if_running, ok_exp=lambda x: x >= 0) == 0

    def speak(self, text):
        self.call(self.bind_speak_text, text)

    def cancel_speech(self):
        self.call(self.bind_cancel_speech)

    def braille_message(self, text):
        self.call(self.bind_braille_message, text)
