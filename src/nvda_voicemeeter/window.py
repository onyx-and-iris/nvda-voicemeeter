import json
import logging
from pathlib import Path

import PySimpleGUI as psg

from .builder import Builder
from .models import (
    _make_bus_mode_cache,
    _make_hardware_outs_cache,
    _make_label_cache,
    _make_output_cache,
    _make_patch_asio_cache,
    _make_patch_insert_cache,
)
from .nvda import Nvda
from .parser import Parser
from .util import (
    _patch_insert_channels,
    get_asio_checkbox_index,
    get_channel_identifier_list,
    get_insert_checkbox_index,
    get_patch_composite_list,
    open_context_menu_for_buttonmenu,
)

logger = logging.getLogger(__name__)

psg.theme("Dark Blue 3")


class NVDAVMWindow(psg.Window):
    """Represents the main window of the Voicemeeter NVDA application"""

    SETTINGS = "settings.json"

    def __init__(self, title, vm):
        self.vm = vm
        self.kind = self.vm.kind
        self.logger = logger.getChild(type(self).__name__)
        self.cache = {
            "outputs": _make_output_cache(self.vm),
            "busmode": _make_bus_mode_cache(self.vm),
            "labels": _make_label_cache(self.vm),
            "asio": _make_patch_asio_cache(self.vm),
            "insert": _make_patch_insert_cache(self.vm),
        }
        self.nvda = Nvda()
        self.parser = Parser()
        self.builder = Builder(self)
        layout = self.builder.run()
        super().__init__(title, layout, return_keyboard_events=True, finalize=True)
        buttonmenu_opts = {"takefocus": 1, "highlightthickness": 1}
        for i in range(self.kind.phys_out):
            self[f"HARDWARE OUT||A{i + 1}"].Widget.config(**buttonmenu_opts)
        if self.kind.name != "basic":
            [self[f"PATCH COMPOSITE||PC{i + 1}"].Widget.config(**buttonmenu_opts) for i in range(self.kind.phys_out)]
            self["ASIO BUFFER"].Widget.config(**buttonmenu_opts)
        self.register_events()

    def __enter__(self):
        settings_path = Path.cwd() / self.SETTINGS
        if settings_path.exists():
            try:
                with open(settings_path, "r") as f:
                    data = json.load(f)
                defaultconfig = Path(data["default_config"])
                if defaultconfig.exists():
                    self.vm.set("command.load", str(defaultconfig))
                    self.logger.debug(f"config {defaultconfig} loaded")
                    self.TKroot.after(
                        200,
                        self.nvda.speak,
                        f"config {defaultconfig.stem} has been loaded",
                    )
            except json.JSONDecodeError:
                self.logger.debug("no data in settings.json. silently continuing...")

        self.vm.init_thread()
        self.vm.observer.add(self.on_pdirty)
        self.TKroot.after(1000, self.enable_parameter_updates)

        return self

    def enable_parameter_updates(self):
        self.vm.event.pdirty = True

    def __exit__(self, exc_type, exc_value, traceback):
        self.vm.end_thread()
        self.close()

    def on_pdirty(self):
        self.cache = {
            "outputs": _make_output_cache(self.vm),
            "busmode": _make_bus_mode_cache(self.vm),
            "labels": _make_label_cache(self.vm),
            "asio": _make_patch_asio_cache(self.vm),
            "insert": _make_patch_insert_cache(self.vm),
        }
        for key, value in self.cache["labels"].items():
            self[key].update(value=value)
        for key, value in self.cache["asio"].items():
            identifier, i = key.split("||")
            partial = get_channel_identifier_list(self.vm)[int(i)]
            self[f"{identifier}||{partial}"].update(value=value)
        for key, value in self.cache["insert"].items():
            identifier, i = key.split("||")
            partial = get_channel_identifier_list(self.vm)[int(i)]
            self[f"{identifier}||{partial}"].update(value=value)

    def register_events(self):
        """Registers events for widgets"""

        # TABS
        self["tabs"].bind("<FocusIn>", "||FOCUS IN")
        self.bind("<Control-KeyPress-Tab>", "CTRL-TAB")
        self.bind("<Control-Shift-KeyPress-Tab>", "CTRL-SHIFT-TAB")

        # Hardware Out
        for i in range(self.vm.kind.phys_out):
            self[f"HARDWARE OUT||A{i + 1}"].bind("<FocusIn>", "||FOCUS IN")
            self[f"HARDWARE OUT||A{i + 1}"].bind("<space>", "||KEY SPACE", propagate=False)
            self[f"HARDWARE OUT||A{i + 1}"].bind("<Return>", "||KEY ENTER", propagate=False)

        # Patch ASIO
        if self.kind.name != "basic":
            for i in range(self.kind.phys_out):
                self[f"ASIO CHECKBOX||IN{i + 1} 0"].bind("<FocusIn>", "||FOCUS IN")
                self[f"ASIO CHECKBOX||IN{i + 1} 1"].bind("<FocusIn>", "||FOCUS IN")

        # Patch Composite
        if self.kind.name != "basic":
            for i in range(self.vm.kind.phys_out):
                self[f"PATCH COMPOSITE||PC{i + 1}"].bind("<FocusIn>", "||FOCUS IN")
                self[f"PATCH COMPOSITE||PC{i + 1}"].bind("<space>", "||KEY SPACE", propagate=False)
                self[f"PATCH COMPOSITE||PC{i + 1}"].bind("<Return>", "||KEY ENTER", propagate=False)

        # Patch Insert
        if self.kind.name != "basic":
            for i in range(self.kind.num_strip):
                if i < self.kind.phys_in:
                    self[f"INSERT CHECKBOX||IN{i + 1} 0"].bind("<FocusIn>", "||FOCUS IN")
                    self[f"INSERT CHECKBOX||IN{i + 1} 1"].bind("<FocusIn>", "||FOCUS IN")
                else:
                    [self[f"INSERT CHECKBOX||IN{i + 1} {j}"].bind("<FocusIn>", "||FOCUS IN") for j in range(8)]

        # Strip Outputs
        for i in range(self.kind.num_strip):
            for j in range(self.kind.phys_out):
                self[f"STRIP {i}||A{j + 1}"].bind("<FocusIn>", "||FOCUS IN")
                self[f"STRIP {i}||A{j + 1}"].bind("<Return>", "||KEY ENTER")
            for j in range(self.kind.virt_out):
                self[f"STRIP {i}||B{j + 1}"].bind("<FocusIn>", "||FOCUS IN")
                self[f"STRIP {i}||B{j + 1}"].bind("<Return>", "||KEY ENTER")

        # Bus Modes
        for i in range(self.kind.num_bus):
            self[f"BUS {i}||MODE"].bind("<FocusIn>", "||FOCUS IN")
            self[f"BUS {i}||MODE"].bind("<Return>", "||KEY ENTER")

        # ASIO Buffer
        if self.kind.name != "basic":
            self["ASIO BUFFER"].bind("<FocusIn>", "||FOCUS IN")
            self["ASIO BUFFER"].bind("<space>", "||KEY SPACE", propagate=False)
            self["ASIO BUFFER"].bind("<Return>", "||KEY ENTER", propagate=False)

    def popup_save_as(self, message, title=None, initial_folder=None):
        layout = [
            [psg.Text(message)],
            [
                psg.FileSaveAs("Browse", initial_folder=str(initial_folder), file_types=(("XML", ".xml"),)),
                psg.Button("Cancel"),
            ],
        ]
        window = psg.Window(title, layout, finalize=True)
        window["Browse"].bind("<FocusIn>", "||FOCUS IN")
        window["Browse"].bind("<Return>", "||KEY ENTER")
        window["Cancel"].bind("<FocusIn>", "||FOCUS IN")
        window["Cancel"].bind("<Return>", "||KEY ENTER")
        filepath = None
        while True:
            event, values = window.read()
            self.logger.debug(f"event::{event}")
            self.logger.debug(f"values::{values}")
            if event in (psg.WIN_CLOSED, "Cancel"):
                break
            elif event.endswith("||FOCUS IN"):
                if values["Browse"]:
                    filepath = values["Browse"]
                    break
                label = event.split("||")[0]
                self.TKroot.after(
                    200 if label == "Edit" else 1,
                    self.nvda.speak,
                    label,
                )
            elif event.endswith("||KEY ENTER"):
                window.find_element_with_focus().click()
        window.close()
        if filepath:
            return Path(filepath)

    def popup_rename(self, message, title=None, tab=None):
        if tab == "Physical Strip":
            upper = self.kind.phys_out + 1
        elif tab == "Virtual Strip":
            upper = self.kind.virt_out + 1
        elif tab == "Buses":
            upper = self.kind.num_bus + 1

        layout = [
            [psg.Text(message)],
            [
                [
                    psg.Spin(
                        list(range(1, upper)), initial_value=1, size=2, enable_events=True, key=f"Index", readonly=True
                    ),
                    psg.Input(key="Edit"),
                ],
                [psg.Button("Ok"), psg.Button("Cancel")],
            ],
        ]
        window = psg.Window(title, layout, finalize=True)
        window["Index"].bind("<FocusIn>", "||FOCUS IN")
        window["Edit"].bind("<FocusIn>", "||FOCUS IN")
        window["Ok"].bind("<FocusIn>", "||FOCUS IN")
        window["Ok"].bind("<Return>", "||KEY ENTER")
        window["Cancel"].bind("<FocusIn>", "||FOCUS IN")
        window["Cancel"].bind("<Return>", "||KEY ENTER")
        data = {}
        while True:
            event, values = window.read()
            self.logger.debug(f"event::{event}")
            self.logger.debug(f"values::{values}")
            if event in (psg.WIN_CLOSED, "Cancel"):
                break
            elif event.endswith("||KEY ENTER"):
                window.find_element_with_focus().click()
            elif event == "Index":
                val = values["Index"]
                self.nvda.speak(f"Index {val}")
            elif event.startswith("Index") and event.endswith("||FOCUS IN"):
                val = values["Index"]
                self.nvda.speak(f"Index {val}")
            elif event.startswith("Edit") and event.endswith("||FOCUS IN"):
                self.nvda.speak("Edit")
            elif event == "Ok":
                data = values
                break
            elif event.startswith("Ok") and event.endswith("||FOCUS IN"):
                self.nvda.speak("Ok")
            elif event.startswith("Cancel") and event.endswith("||FOCUS IN"):
                self.nvda.speak("Cancel")

        window.close()
        return data

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

            match parsed_cmd := self.parser.match.parseString(event):
                # Focus tabgroup
                case ["CTRL-TAB"] | ["CTRL-SHIFT-TAB"]:
                    self["tabs"].set_focus()

                # Rename popups
                case ["F2:113"]:
                    tab = values["tabs"]
                    if tab in ("Physical Strip", "Virtual Strip", "Buses"):
                        data = self.popup_rename("Label", title=f"Rename {tab}", tab=tab)
                        if not data:  # cancel was pressed
                            continue
                        index = int(data["Index"]) - 1
                        match tab:
                            case "Physical Strip":
                                label = data.get("Edit") or f"Hardware Input {index + 1}"
                                self.vm.strip[index].label = label
                                self[f"STRIP {index}||LABEL"].update(value=label)
                                self.cache["labels"][f"STRIP {index}||LABEL"] = label
                            case "Virtual Strip":
                                label = data.get("Edit") or f"Virtual Input {index + 1}"
                                self.vm.strip[index].label = label
                                self[f"STRIP {index}||LABEL"].update(value=label)
                                self.cache["labels"][f"STRIP {index}||LABEL"] = label
                            case "Buses":
                                if index < self.kind.phys_out:
                                    label = data.get("Edit") or f"Physical Bus {index + 1}"
                                else:
                                    label = data.get("Edit") or f"Virtual Bus {index - self.kind.phys_out + 1}"
                                self.vm.bus[index].label = label
                                self[f"BUS {index}||LABEL"].update(value=label)
                                self.cache["labels"][f"BUS {index}||LABEL"] = label

                # Menus
                case [["Restart", "Audio", "Engine"], ["MENU"]]:
                    self.perform_long_operation(self.vm.command.restart, "ENGINE RESTART||END")
                case [["ENGINE", "RESTART"], ["END"]]:
                    self.TKroot.after(
                        200,
                        self.nvda.speak,
                        "Audio Engine restarted",
                    )
                case [["Save", "Settings"], ["MENU"]]:
                    initial_folder = Path.home() / "Documents" / "Voicemeeter"
                    if filepath := self.popup_save_as(
                        "Open the file browser", title="Save As", initial_folder=initial_folder
                    ):
                        self.vm.set("command.save", str(filepath))
                        self.logger.debug(f"saving config file to {filepath}")
                        self.TKroot.after(
                            200,
                            self.nvda.speak,
                            f"config file {filepath.stem} has been saved",
                        )
                case [["Load", "Settings"], ["MENU"]]:
                    initial_folder = Path.home() / "Documents" / "Voicemeeter"
                    if filepath := psg.popup_get_file(
                        "Filename",
                        title="Load Settings",
                        initial_folder=initial_folder,
                        no_window=True,
                        file_types=(("XML", ".xml"),),
                    ):
                        filepath = Path(filepath)
                        self.vm.set("command.load", str(filepath))
                        self.logger.debug(f"loading config file from {filepath}")
                        self.TKroot.after(
                            200,
                            self.nvda.speak,
                            f"config file {filepath.stem} has been loaded",
                        )
                case [["Load", "Settings", "on", "Startup"], ["MENU"]]:
                    initial_folder = Path.home() / "Documents" / "Voicemeeter"
                    if filepath := psg.popup_get_file(
                        "Filename",
                        title="Load Settings",
                        initial_folder=initial_folder,
                        no_window=True,
                        file_types=(("XML", ".xml"),),
                    ):
                        filepath = Path(filepath)
                        with open(self.SETTINGS, "w") as f:
                            json.dump({"default_config": str(filepath)}, f)
                        self.TKroot.after(
                            200,
                            self.nvda.speak,
                            f"config {filepath.stem} set as default on startup",
                        )
                    else:
                        with open(self.SETTINGS, "wb") as f:
                            f.truncate()
                        self.logger.debug("default bin was truncated")

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
                case [["HARDWARE", "OUT"], [key], ["KEY", "SPACE" | "ENTER"]]:
                    open_context_menu_for_buttonmenu(self, f"HARDWARE OUT||{key}")

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
                case [["PATCH", "COMPOSITE"], [key], ["KEY", "SPACE" | "ENTER"]]:
                    open_context_menu_for_buttonmenu(self, f"PATCH COMPOSITE||{key}")

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

                # ASIO Buffer
                case ["ASIO BUFFER"]:
                    if values[event] == "Default":
                        val = 0
                    else:
                        val = values[event]
                    self.vm.option.buffer("asio", val)
                    self.TKroot.after(200, self.nvda.speak, f"ASIO BUFFER {val if val else 'default'}")
                case [["ASIO", "BUFFER"], ["FOCUS", "IN"]]:
                    val = int(self.vm.get("option.buffer.asio"))
                    self.nvda.speak(f"ASIO BUFFER {val if val else 'default'}")
                case [["ASIO", "BUFFER"], ["KEY", "SPACE" | "ENTER"]]:
                    open_context_menu_for_buttonmenu(self, "ASIO BUFFER")

                # Strip outputs
                case [["STRIP", index], [output]]:
                    val = not self.cache["outputs"][f"STRIP {index}||{output}"]
                    setattr(self.vm.strip[int(index)], output, val)
                    self.cache["outputs"][f"STRIP {index}||{output}"] = val
                    self.nvda.speak(f"STRIP {index} {output} {label if label else ''} {'on' if val else 'off'}")
                case [["STRIP", index], [output], ["FOCUS", "IN"]]:
                    val = self.cache["outputs"][f"STRIP {index}||{output}"]
                    label = self.cache["labels"][f"STRIP {index}||LABEL"]
                    self.nvda.speak(f"{label} {output} {'on' if val else 'off'}")
                case [["STRIP", index], [output], ["KEY", "ENTER"]]:
                    self.find_element_with_focus().click()

                # Bus modes
                case [["BUS", index], ["MODE"]]:
                    val = self.cache["busmode"][event]
                    if val != "normal":
                        self.vm.bus[int(index)].mode.normal = True
                        self.cache["busmode"][event] = "normal"
                    else:
                        self.vm.bus[int(index)].mode.composite = True
                        self.cache["busmode"][event] = "composite"
                    label = self.cache["labels"][f"BUS {index}||LABEL"]
                    self.TKroot.after(
                        200,
                        self.nvda.speak,
                        f"{label} bus mode {self.cache['busmode'][event]}",
                    )
                case [["BUS", index], ["MODE"], ["FOCUS", "IN"]]:
                    label = self.cache["labels"][f"BUS {index}||LABEL"]
                    self.nvda.speak(f"{label} bus mode {self.cache['busmode'][f'BUS {index}||MODE']}")
                case [["BUS", index], ["MODE"], ["KEY", "ENTER"]]:
                    self.find_element_with_focus().click()

                # Unknown
                case _:
                    self.logger.debug(f"Unknown event {event}")
            self.logger.debug(f"parsed::{parsed_cmd}")


def request_window_object(kind_id, vm):
    NVDAVMWindow_cls = NVDAVMWindow
    return NVDAVMWindow_cls(f"Voicemeeter {kind_id.capitalize()} NVDA", vm)
