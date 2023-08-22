from .cdll import libc


class CBindings:
    bind_test_if_running = libc.nvdaController_testIfRunning
    bind_speak_text = libc.nvdaController_speakText
    bind_cancel_speech = libc.nvdaController_cancelSpeech
    bind_braille_message = libc.nvdaController_brailleMessage

    def call(self, fn, *args, ok=(0,)):
        retval = fn(*args)
        if retval not in ok:
            raise RuntimeError(f"{fn.__name__} returned {retval}")
        return retval


class Nvda(CBindings):
    @property
    def is_running(self):
        return self.call(self.bind_test_if_running, ok=(0, 1)) == 0

    def speak(self, text):
        self.call(self.bind_speak_text, text)

    def cancel_speech(self):
        self.call(self.bind_cancel_speech)

    def braille_message(self, text):
        self.call(self.bind_braille_message, text)
