import logging

import PySimpleGUI as psg

from .builder import Builder
from .models import _make_output_cache, _patch_insert_channels
from .nvda import Nvda
from .parser import Parser
from .util import (
    get_asio_checkbox_index,
    get_insert_checkbox_index,
    get_patch_composite_list,
)

logger = logging.getLogger(__name__)

psg.theme("Dark Blue 3")


class NVDAVMWindow(psg.Window):
    """Represents the main window of the Voicemeeter NVDA application"""

    def __init__(self, title, vm):
        self.vm = vm
        self.kind = self.vm.kind
        self.logger = logger.getChild(type(self).__name__)
        self.cache = {"outputs": _make_output_cache(self.vm)}
        self.nvda = Nvda()
        self.parser = Parser()
        self.builder = Builder(self)
        layout = self.builder.run()
        super().__init__(title, layout, finalize=True)
        [self[f"HARDWARE OUT||A{i + 1}"].Widget.config(takefocus=1) for i in range(self.kind.phys_out)]
        [self[f"PATCH COMPOSITE||PC{i + 1}"].Widget.config(takefocus=1) for i in range(self.kind.phys_out)]
        self.register_events()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def register_events(self):
        """Registers events for widgets"""

        # TABS
        self["tabs"].bind("<FocusIn>", "||FOCUS IN")

        # Hardware Out
        for i in range(self.vm.kind.phys_out):
            self[f"HARDWARE OUT||A{i + 1}"].bind("<FocusIn>", "||FOCUS IN")

        # Patch ASIO
        if self.kind.name != "basic":
            for i in range(self.kind.phys_out):
                self[f"ASIO CHECKBOX||IN{i + 1} 0"].bind("<FocusIn>", "||FOCUS IN")
                self[f"ASIO CHECKBOX||IN{i + 1} 1"].bind("<FocusIn>", "||FOCUS IN")

        # Patch Composite
        for i in range(self.vm.kind.phys_out):
            self[f"PATCH COMPOSITE||PC{i + 1}"].bind("<FocusIn>", "||FOCUS IN")

        # Patch Insert
        if self.kind.name != "basic":
            for i in range(self.kind.num_strip):
                if i <= self.kind.phys_in:
                    self[f"INSERT CHECKBOX||IN{i + 1} 0"].bind("<FocusIn>", "||FOCUS IN")
                    self[f"INSERT CHECKBOX||IN{i + 1} 1"].bind("<FocusIn>", "||FOCUS IN")
                else:
                    [self[f"INSERT CHECKBOX||IN{i + 1} {j}"].bind("<FocusIn>", "||FOCUS IN") for j in range(8)]

        # Strip Outputs
        for i in range(self.kind.num_strip):
            for j in range(self.kind.phys_out):
                self[f"STRIP {i}||A{j + 1}"].bind("<FocusIn>", "||FOCUS IN")
            for j in range(self.kind.virt_out):
                self[f"STRIP {i}||B{j + 1}"].bind("<FocusIn>", "||FOCUS IN")

    def run(self):
        """
        Parses the event string and matches it to events

        Main thread will shutdown once a close or exit event occurs
        """

        while True:
            event, values = self.read()
            self.logger.debug(f"event::{event}")
            self.logger.debug(f"values::{values}")
            if event in (psg.WIN_CLOSED, "Exit"):
                break
            elif event == "tabs":
                self.nvda.speak(f"tab {values['tabs']}")
                continue

            match parsed_cmd := self.parser.match.parseString(event):
                # Tabs
                case [["tabs"], ["FOCUS", "IN"]]:
                    self.nvda.speak(f"tab {values['tabs']}")

                # Hardware out
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

                # Patch ASIO
                case [["ASIO", "CHECKBOX"], [in_num, channel]]:
                    index = get_asio_checkbox_index(int(channel), int(in_num[-1]))
                    val = values[f"ASIO CHECKBOX||{in_num} {channel}"]
                    self.vm.patch.asio[index].set(val)
                    channel = ("left", "right")[int(channel)]
                    self.nvda.speak(f"Patch ASIO {in_num} {channel} set to {val}")
                case [["ASIO", "CHECKBOX"], [in_num, channel], ["FOCUS", "IN"]]:
                    val = values[f"ASIO CHECKBOX||{in_num} {channel}"]
                    channel = ("left", "right")[int(channel)]
                    num = int(in_num[-1])
                    self.nvda.speak(f"Patch ASIO inputs to strips IN#{num} {channel} {val}")

                # Patch COMPOSITE
                case [["PATCH", "COMPOSITE"], [key]]:
                    val = values[f"PATCH COMPOSITE||{key}"]
                    index = int(key[-1]) - 1
                    self.vm.patch.composite[index].set(get_patch_composite_list(self.kind).index(val) + 1)
                    self.TKroot.after(200, self.nvda.speak, f"PATCH COMPOSITE {key[-1]} set {val}")
                case [["PATCH", "COMPOSITE"], [key], ["FOCUS", "IN"]]:
                    if values[f"PATCH COMPOSITE||{key}"]:
                        val = values[f"PATCH COMPOSITE||{key}"]
                    else:
                        index = int(key[-1]) - 1
                        val = get_patch_composite_list(self.kind)[self.vm.patch.composite[index].get() - 1]
                    self.nvda.speak(f"Patch COMPOSITE {key[-1]} {val}")

                # Patch INSERT
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

                # Strip outputs
                case [["STRIP", index], [output]]:
                    val = not self.cache["outputs"][f"STRIP {index}||{output}"]
                    setattr(self.vm.strip[int(index)], output, val)
                    self.cache["outputs"][f"STRIP {index}||{output}"] = val
                case [["STRIP", index], [output], ["FOCUS", "IN"]]:
                    val = self.cache["outputs"][f"STRIP {index}||{output}"]
                    label = self.vm.strip[int(index)].label
                    self.nvda.speak(f"STRIP {index} {output} {label if label else ''} {'on' if val else 'off'}")
                case _:
                    self.logger.error(f"Unknown event {event}")
            self.logger.debug(parsed_cmd)


def request_window_object(title, vm):
    NVDAVMWindow_cls = NVDAVMWindow
    return NVDAVMWindow_cls(title, vm)
