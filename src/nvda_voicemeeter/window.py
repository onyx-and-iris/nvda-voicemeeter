import logging

import PySimpleGUI as psg

from .builder import Builder
from .models import _make_cache, _patch_insert_channels
from .nvda import Nvda
from .parser import Parser
from .util import get_asio_checkbox_index, get_insert_checkbox_index

logger = logging.getLogger(__name__)

psg.theme("Dark Blue 3")


class Window(psg.Window):
    """Represents the main window of the application"""

    def __init__(self, title, vm):
        self.vm = vm
        self.kind = self.vm.kind
        self.logger = logger.getChild(type(self).__name__)
        self.cache = {}
        self.nvda = Nvda()
        self.parser = Parser()
        self.builder = Builder(self, self.vm)
        layout = self.builder.run()
        super().__init__(title, layout, finalize=True)
        [self[f"HARDWARE OUT||A{i}"].Widget.config(takefocus=1) for i in range(1, self.kind.phys_out + 1)]
        [self[f"PATCH COMPOSITE||PC{i}"].Widget.config(takefocus=1) for i in range(1, self.kind.phys_out + 1)]
        self.register_events()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def register_events(self):
        # Hardware Out events
        for i in range(1, self.vm.kind.phys_out + 1):
            self[f"HARDWARE OUT||A{i}"].bind("<FocusIn>", "||FOCUS IN")

        # Patch ASIO events
        if self.kind.name != "basic":
            for i in range(1, self.kind.phys_out + 1):
                self[f"ASIO CHECKBOX||IN{i} 0"].bind("<FocusIn>", "||FOCUS IN")
                self[f"ASIO CHECKBOX||IN{i} 1"].bind("<FocusIn>", "||FOCUS IN")

        # Patch Composite events
        for i in range(1, self.vm.kind.phys_out + 1):
            self[f"PATCH COMPOSITE||PC{i}"].bind("<FocusIn>", "||FOCUS IN")

        # Patch Insert events
        if self.kind.name != "basic":
            for i in range(1, self.kind.num_strip + 1):
                if i <= self.kind.phys_in:
                    self[f"INSERT CHECKBOX||IN{i} 0"].bind("<FocusIn>", "||FOCUS IN")
                    self[f"INSERT CHECKBOX||IN{i} 1"].bind("<FocusIn>", "||FOCUS IN")
                else:
                    [self[f"INSERT CHECKBOX||IN{i} {j}"].bind("<FocusIn>", "||FOCUS IN") for j in range(8)]

    def run(self):
        """
        Parses the event string and matches it to events

        Main thread will shutdown once a close or exit event occurs
        """
        while True:
            event, values = self.read()
            if event in (psg.WIN_CLOSED, "Exit"):
                break
            match parsed_cmd := self.parser.match.parseString(event):
                case [["HARDWARE", "OUT"], [key]]:
                    selection = values[f"HARDWARE OUT||{key}"]
                    index = int(key[1]) - 1
                    match selection.split(":"):
                        case [device_name]:
                            setattr(self.vm.bus[index].device, "wdm", "")
                            self.TKroot.after(200, self.nvda.speak, f"HARDWARE OUT {key} device selection removed")
                        case [driver, device_name]:
                            setattr(self.vm.bus[index].device, driver, device_name.strip())
                            phonetic = {"mme": "em em e"}
                            self.TKroot.after(
                                200,
                                self.nvda.speak,
                                f"HARDWARE OUT {key} set {phonetic.get(driver, driver)} {device_name}",
                            )
                case [["HARDWARE", "OUT"], [key], ["FOCUS", "IN"]]:
                    self.nvda.speak(f"HARDWARE OUT {key} {self.vm.bus[int(key[-1]) - 1].device.name}")
                case [["ASIO", "CHECKBOX"], [in_num, channel]]:
                    index = get_asio_checkbox_index(int(channel), int(in_num[-1]))
                    val = values[f"ASIO CHECKBOX||{in_num} {channel}"]
                    self.vm.patch.asio[index].set(val)
                    channel = ("left", "right")[int(channel)]
                    self.nvda.speak(f"Patch ASIO {in_num} {channel} set to {val}")
                case [["ASIO", "CHECKBOX"], [in_num, channel], ["FOCUS", "IN"]]:
                    val = values[f"ASIO CHECKBOX||{in_num} {channel}"]
                    index = get_asio_checkbox_index(int(channel), int(in_num[-1]))
                    channel = ("left", "right")[int(channel)]
                    num = int(in_num[-1])
                    self.nvda.speak(f"Patch ASIO inputs to strips IN#{num} {channel} {val}")
                case [["INSERT", "CHECKBOX"], [in_num, channel]]:
                    index = get_insert_checkbox_index(
                        self.kind,
                        int(channel),
                        int(in_num[-1]),
                    )
                    val = values[f"INSERT CHECKBOX||{in_num} {channel}"]
                    self.vm.patch.insert[index].on = val
                    self.nvda.speak(
                        f"PATCH INSERT {in_num} {_patch_insert_channels[int(channel)]} set to {'on' if val else 'off'}"
                    )
                case [["INSERT", "CHECKBOX"], [in_num, channel], ["FOCUS", "IN"]]:
                    index = get_insert_checkbox_index(
                        self.kind,
                        int(channel),
                        int(in_num[-1]),
                    )
                    val = values[f"INSERT CHECKBOX||{in_num} {channel}"]
                    channel = _patch_insert_channels[int(channel)]
                    num = int(in_num[-1])
                    self.nvda.speak(f"Patch INSERT IN#{num} {channel} {'on' if val else 'off'}")
                case _:
                    self.logger.error(f"Unknown event {event}")
            self.logger.debug(parsed_cmd)


def request_window_object(title, vm):
    WINDOW_cls = Window
    return WINDOW_cls(title, vm)
