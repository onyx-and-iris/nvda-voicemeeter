import PySimpleGUI as psg

from .models import _make_cache
from .nvda import Nvda
from .parser import Parser


class Window(psg.Window):
    def __init__(self, title, vm):
        self.vm = vm
        self.kind = self.vm.kind
        super().__init__(title, self.make_layout(), finalize=True)
        self.cache = _make_cache(self.vm)
        self.nvda = Nvda()
        self.parser = Parser()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def make_layout(self) -> list:
        """Builds the window layout step by step"""

        def add_physical_device_opts(layout):
            devices = ["{type}: {name}".format(**self.vm.device.output(i)) for i in range(self.vm.device.outs)]
            layout.append(
                [
                    psg.Combo(
                        devices,
                        size=(22, 4),
                        expand_x=True,
                        enable_events=True,
                        key=f"DEVICE LIST||PHYSOUT {i}",
                    )
                    for i in range(self.kind.phys_out)
                ]
            )

        upper_layout = list()
        [step(upper_layout) for step in (add_physical_device_opts,)]
        row0 = psg.Frame("Hardware Out", upper_layout)

        return [[row0]]

    def run(self):
        """Runs the main window until an Close/Exit event"""
        while True:
            event, values = self.read()
            if event in (psg.WIN_CLOSED, "Exit"):
                break
            match self.parser.match.parseString(event):
                case _:
                    pass


def request_window_object(title, vm):
    WINDOW_cls = Window
    return WINDOW_cls(title, vm)
