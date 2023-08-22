import logging

import PySimpleGUI as psg

from .builder import Builder
from .models import _make_cache
from .nvda import Nvda
from .parser import Parser

logger = logging.getLogger(__name__)


class Window(psg.Window):
    """Represents the main window of the application"""

    def __init__(self, title, vm):
        self.vm = vm
        self.kind = self.vm.kind
        self.logger = logger.getChild(type(self).__name__)
        self.cache = _make_cache(self.vm)
        self.nvda = Nvda()
        self.parser = Parser()
        self.builder = Builder(self, self.vm)
        layout = self.builder.run()
        super().__init__(title, layout, finalize=True)
        self.register_events()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def register_events(self):
        for i in range(1, self.vm.kind.phys_out + 1):
            self[f"HARDWARE OUT||A{i}"].bind("<FocusIn>", "||FOCUS IN")
        for i in range(1, self.kind.phys_out + 1):
            self[f"ASIO CHECKBOX||IN{i} 0"].bind("<FocusIn>", "||FOCUS IN")
            self[f"ASIO CHECKBOX||IN{i} 1"].bind("<FocusIn>", "||FOCUS IN")
        for i in range(1, self.kind.num_strip + 1):
            if i <= self.kind.phys_in:
                self[f"INSERT CHECKBOX||IN{i} 0"].bind("<FocusIn>", "||FOCUS IN")
                self[f"INSERT CHECKBOX||IN{i} 1"].bind("<FocusIn>", "||FOCUS IN")
            else:
                self[f"INSERT CHECKBOX||IN{i} 0"].bind("<FocusIn>", "||FOCUS IN")
                self[f"INSERT CHECKBOX||IN{i} 1"].bind("<FocusIn>", "||FOCUS IN")
                self[f"INSERT CHECKBOX||IN{i} 2"].bind("<FocusIn>", "||FOCUS IN")
                self[f"INSERT CHECKBOX||IN{i} 3"].bind("<FocusIn>", "||FOCUS IN")
                self[f"INSERT CHECKBOX||IN{i} 4"].bind("<FocusIn>", "||FOCUS IN")
                self[f"INSERT CHECKBOX||IN{i} 5"].bind("<FocusIn>", "||FOCUS IN")
                self[f"INSERT CHECKBOX||IN{i} 6"].bind("<FocusIn>", "||FOCUS IN")
                self[f"INSERT CHECKBOX||IN{i} 7"].bind("<FocusIn>", "||FOCUS IN")

    def run(self):
        """
        Parses the event string and matches it to events

        Main thread will shutdown once a close or exit event occurs
        """
        while True:
            event, values = self.read()
            if event in (psg.WIN_CLOSED, "Exit"):
                break
            match self.parser.match.parseString(event):
                case [["HARDWARE", "OUT"], [key]]:
                    selection = values[f"HARDWARE OUT||{key}"]
                    match selection.split(":"):
                        case [device_name]:
                            device_name = ""
                            self.nvda.speak(f"HARDWARE OUT {key} device deselected")
                        case [driver, device_name]:
                            index = int(key[1]) - 1
                            setattr(self.vm.bus[index].device, driver, device_name.strip())
                            self.nvda.speak(f"{driver} {selection}")
                case [["HARDWARE", "OUT"], [key], ["FOCUS", "IN"]]:
                    self.nvda.speak(f"HARDWARE OUT {key} in focus")
                case [["ASIO", "CHECKBOX"], [in_num, side]]:
                    if int(side) == 0:
                        index = (2 * int(in_num[-1])) - 2
                    else:
                        index = 2 * int(in_num[-1]) - 1
                    val = values[f"ASIO CHECKBOX||{in_num} {side}"]
                    self.vm.patch.asio[index].set(val)
                    side = ("left", "right")[int(side)]
                    self.nvda.speak(f"Patch ASIO {in_num} {side} set to {val}")
                case [["ASIO", "CHECKBOX"], [in_num, side], ["FOCUS", "IN"]]:
                    side = ("left", "right")[int(side)]
                    num = int(in_num[-1])
                    self.nvda.speak(f"Patch ASIO inputs to strips IN#{num} {side} in focus")
                case _:
                    self.logger.error(f"Unknown event {event}")
            self.logger.debug(self.parser.match.parseString(event))


def request_window_object(title, vm):
    WINDOW_cls = Window
    return WINDOW_cls(title, vm)
