import logging

import PySimpleGUI as psg

from .models import _make_cache
from .nvda import Nvda
from .parser import Parser

logger = logging.getLogger(__name__)


class Window(psg.Window):
    def __init__(self, title, vm):
        self.vm = vm
        self.kind = self.vm.kind
        super().__init__(title, self.make_layout(), finalize=True)
        self.logger = logger.getChild(type(self).__name__)
        self.cache = _make_cache(self.vm)
        self.nvda = Nvda()
        self.parser = Parser()
        self.register_events()

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
                        key=f"HARDWARE OUT||A{i}",
                    )
                    for i in range(1, self.kind.phys_out + 1)
                ]
            )

        hardware_out = list()
        [step(hardware_out) for step in (add_physical_device_opts,)]
        row0 = psg.Frame("Hardware Out", hardware_out)

        return [[row0]]

    def register_events(self):
        for i in range(1, self.vm.kind.phys_out + 1):
            self[f"HARDWARE OUT||A{i}"].bind("<FocusIn>", "||FOCUS IN")

    def run(self):
        """Runs the main window until an Close/Exit event"""
        while True:
            event, values = self.read()
            if event in (psg.WIN_CLOSED, "Exit"):
                break
            match self.parser.match.parseString(event):
                case [["HARDWARE", "OUT"], [key]]:
                    selection = values[f"HARDWARE OUT||{key}"]
                    driver, device_name = selection.split(":")
                    index = int(key[1]) - 1
                    setattr(self.vm.bus[index].device, driver, device_name.strip())
                    self.nvda.speak(f"{driver} {selection}")
                case [["HARDWARE", "OUT"], [key], ["FOCUS", "IN"]]:
                    self.nvda.speak(f"HARDWARE OUT {key} in focus")
                case _:
                    print(f"Unknown event {event}")
            self.logger.debug(self.parser.match.parseString(event))


def request_window_object(title, vm):
    WINDOW_cls = Window
    return WINDOW_cls(title, vm)
