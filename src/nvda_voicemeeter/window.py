import json
import logging
from pathlib import Path

import PySimpleGUI as psg

from . import models, util
from .builder import Builder
from .nvda import Nvda
from .parser import Parser

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
            "hw_ins": models._make_hardware_ins_cache(self.vm),
            "hw_outs": models._make_hardware_outs_cache(self.vm),
            "strip": models._make_param_cache(self.vm, "strip"),
            "bus": models._make_param_cache(self.vm, "bus"),
            "labels": models._make_label_cache(self.vm),
            "asio": models._make_patch_asio_cache(self.vm),
            "insert": models._make_patch_insert_cache(self.vm),
        }
        self.nvda = Nvda()
        self.parser = Parser()
        self.builder = Builder(self)
        layout = self.builder.run()
        super().__init__(title, layout, return_keyboard_events=True, finalize=True)
        buttonmenu_opts = {"takefocus": 1, "highlightthickness": 1}
        for i in range(self.kind.phys_in):
            self[f"HARDWARE IN||{i + 1}"].Widget.config(**buttonmenu_opts)
        for i in range(self.kind.phys_out):
            self[f"HARDWARE OUT||A{i + 1}"].Widget.config(**buttonmenu_opts)
        if self.kind.name == "basic":
            self[f"HARDWARE OUT||A2"].Widget.config(**buttonmenu_opts)
        if self.kind.name != "basic":
            [self[f"PATCH COMPOSITE||PC{i + 1}"].Widget.config(**buttonmenu_opts) for i in range(self.kind.phys_out)]
        slider_opts = {"takefocus": 1, "highlightthickness": 1}
        for i in range(self.kind.num_strip):
            for param in util.get_slider_params(i, self.vm):
                self[f"STRIP {i}||SLIDER {param}"].Widget.config(**slider_opts)
            self[f"STRIP {i}||SLIDER GAIN"].Widget.config(**slider_opts)
            if self.kind.name != "basic":
                self[f"STRIP {i}||SLIDER LIMIT"].Widget.config(**slider_opts)
        for i in range(self.kind.num_bus):
            self[f"BUS {i}||SLIDER GAIN"].Widget.config(**slider_opts)

        self.register_events()
        self["tabgroup"].set_focus()

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
            "hw_ins": models._make_hardware_ins_cache(self.vm),
            "hw_outs": models._make_hardware_outs_cache(self.vm),
            "strip": models._make_param_cache(self.vm, "strip"),
            "bus": models._make_param_cache(self.vm, "bus"),
            "labels": models._make_label_cache(self.vm),
            "asio": models._make_patch_asio_cache(self.vm),
            "insert": models._make_patch_insert_cache(self.vm),
        }
        for key, value in self.cache["labels"].items():
            self[key].update(value=value)
            self[f"{key}||SLIDER"].update(value=value)
        for i in range(self.kind.num_strip):
            self[f"STRIP {i}||SLIDER GAIN"].update(value=self.vm.strip[i].gain)
            if self.kind.name != "basic":
                self[f"STRIP {i}||SLIDER LIMIT"].update(value=self.vm.strip[i].limit)
            for param in util.get_slider_params(i, self.vm):
                if param in ("AUDIBILITY", "BASS", "MID", "TREBLE"):
                    val = getattr(self.vm.strip[i], param.lower())
                else:
                    target = getattr(self.vm.strip[i], param.lower())
                    val = target.knob
                self[f"STRIP {i}||SLIDER {param}"].update(value=val)
        for i in range(self.kind.num_bus):
            self[f"BUS {i}||SLIDER GAIN"].update(value=self.vm.bus[i].gain)
        if self.kind.name != "basic":
            for key, value in self.cache["asio"].items():
                identifier, i = key.split("||")
                partial = util.get_channel_identifier_list(self.vm)[int(i)]
                self[f"{identifier}||{partial}"].update(value=value)
            for key, value in self.cache["insert"].items():
                identifier, i = key.split("||")
                partial = util.get_channel_identifier_list(self.vm)[int(i)]
                self[f"{identifier}||{partial}"].update(value=value)

    def register_events(self):
        """Registers events for widgets"""

        # TABS
        self["tabgroup"].bind("<FocusIn>", "||FOCUS IN")
        for tabname in util.get_tabs_labels()[1:]:
            self[f"tabgroup||{tabname}"].bind("<FocusIn>", "||FOCUS IN")
            self[f"tabgroup||{tabname}"].bind("<Shift-KeyPress-Tab>", "||KEY SHIFT TAB")
        self.bind("<Control-KeyPress-Tab>", "CTRL-TAB")
        self.bind("<Control-Shift-KeyPress-Tab>", "CTRL-SHIFT-TAB")
        self.bind("<Control-a>", "CTRL-A")

        # Hardware In
        for i in range(self.vm.kind.phys_in):
            self[f"HARDWARE IN||{i + 1}"].bind("<FocusIn>", "||FOCUS IN")
            self[f"HARDWARE IN||{i + 1}"].bind("<space>", "||KEY SPACE", propagate=False)
            self[f"HARDWARE IN||{i + 1}"].bind("<Return>", "||KEY ENTER", propagate=False)

        # Hardware Out
        for i in range(self.vm.kind.phys_out):
            self[f"HARDWARE OUT||A{i + 1}"].bind("<FocusIn>", "||FOCUS IN")
            self[f"HARDWARE OUT||A{i + 1}"].bind("<space>", "||KEY SPACE", propagate=False)
            self[f"HARDWARE OUT||A{i + 1}"].bind("<Return>", "||KEY ENTER", propagate=False)
        if self.vm.kind.name == "basic":
            self[f"HARDWARE OUT||A2"].bind("<FocusIn>", "||FOCUS IN")
            self[f"HARDWARE OUT||A2"].bind("<space>", "||KEY SPACE", propagate=False)
            self[f"HARDWARE OUT||A2"].bind("<Return>", "||KEY ENTER", propagate=False)

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

        # Advanced Settings
        self["ADVANCED SETTINGS"].bind("<FocusIn>", "||FOCUS IN")
        self["ADVANCED SETTINGS"].bind("<Return>", "||KEY ENTER")

        # Strip Params
        for i in range(self.kind.num_strip):
            for j in range(self.kind.phys_out):
                self[f"STRIP {i}||A{j + 1}"].bind("<FocusIn>", "||FOCUS IN")
                self[f"STRIP {i}||A{j + 1}"].bind("<Return>", "||KEY ENTER")
            for j in range(self.kind.virt_out):
                self[f"STRIP {i}||B{j + 1}"].bind("<FocusIn>", "||FOCUS IN")
                self[f"STRIP {i}||B{j + 1}"].bind("<Return>", "||KEY ENTER")
            if i < self.kind.phys_in:
                for param in ("MONO", "SOLO", "MUTE"):
                    self[f"STRIP {i}||{param}"].bind("<FocusIn>", "||FOCUS IN")
                    self[f"STRIP {i}||{param}"].bind("<Return>", "||KEY ENTER")
            else:
                for param in ("MONO", "SOLO", "MUTE"):
                    self[f"STRIP {i}||{param}"].bind("<FocusIn>", "||FOCUS IN")
                    self[f"STRIP {i}||{param}"].bind("<Return>", "||KEY ENTER")

        # Strip Sliders
        for i in range(self.kind.num_strip):
            for param in util.get_slider_params(i, self.vm) + ("GAIN", "LIMIT"):
                if self.kind.name == "basic" and param == "LIMIT":
                    continue
                self[f"STRIP {i}||SLIDER {param}"].bind("<FocusIn>", "||FOCUS IN")
                self[f"STRIP {i}||SLIDER {param}"].bind("<FocusOut>", "||FOCUS OUT")
                self[f"STRIP {i}||SLIDER {param}"].bind("<Left>", "||KEY LEFT")
                self[f"STRIP {i}||SLIDER {param}"].bind("<Right>", "||KEY RIGHT")
                self[f"STRIP {i}||SLIDER {param}"].bind("<Shift-KeyPress-Left>", "||KEY SHIFT LEFT")
                self[f"STRIP {i}||SLIDER {param}"].bind("<Shift-KeyPress-Right>", "||KEY SHIFT RIGHT")
                self[f"STRIP {i}||SLIDER {param}"].bind("<Control-KeyPress-Left>", "||KEY CTRL LEFT")
                self[f"STRIP {i}||SLIDER {param}"].bind("<Control-KeyPress-Right>", "||KEY CTRL RIGHT")
                self[f"STRIP {i}||SLIDER {param}"].bind("<Up>", "||KEY UP")
                self[f"STRIP {i}||SLIDER {param}"].bind("<Down>", "||KEY DOWN")
                self[f"STRIP {i}||SLIDER {param}"].bind("<Shift-KeyPress-Up>", "||KEY SHIFT UP")
                self[f"STRIP {i}||SLIDER {param}"].bind("<Shift-KeyPress-Down>", "||KEY SHIFT DOWN")
                self[f"STRIP {i}||SLIDER {param}"].bind("<Control-KeyPress-Up>", "||KEY CTRL UP")
                self[f"STRIP {i}||SLIDER {param}"].bind("<Control-KeyPress-Down>", "||KEY CTRL DOWN")

        # Bus Params
        params = ["MONO", "EQ", "MUTE", "MODE"]
        if self.vm.kind.name == "basic":
            params.remove("EQ")
        for i in range(self.kind.num_bus):
            for param in params:
                self[f"BUS {i}||{param}"].bind("<FocusIn>", "||FOCUS IN")
                self[f"BUS {i}||{param}"].bind("<Return>", "||KEY ENTER")

        # Bus Sliders
        for i in range(self.kind.num_bus):
            self[f"BUS {i}||SLIDER GAIN"].bind("<FocusIn>", "||FOCUS IN")
            self[f"BUS {i}||SLIDER GAIN"].bind("<FocusOut>", "||FOCUS OUT")
            self[f"BUS {i}||SLIDER GAIN"].bind("<Left>", "||KEY LEFT")
            self[f"BUS {i}||SLIDER GAIN"].bind("<Right>", "||KEY RIGHT")
            self[f"BUS {i}||SLIDER GAIN"].bind("<Shift-KeyPress-Left>", "||KEY SHIFT LEFT")
            self[f"BUS {i}||SLIDER GAIN"].bind("<Shift-KeyPress-Right>", "||KEY SHIFT RIGHT")
            self[f"BUS {i}||SLIDER GAIN"].bind("<Control-KeyPress-Left>", "||KEY CTRL LEFT")
            self[f"BUS {i}||SLIDER GAIN"].bind("<Control-KeyPress-Right>", "||KEY CTRL RIGHT")
            self[f"BUS {i}||SLIDER GAIN"].bind("<Up>", "||KEY UP")
            self[f"BUS {i}||SLIDER GAIN"].bind("<Down>", "||KEY DOWN")
            self[f"BUS {i}||SLIDER GAIN"].bind("<Shift-KeyPress-Up>", "||KEY SHIFT UP")
            self[f"BUS {i}||SLIDER GAIN"].bind("<Shift-KeyPress-Down>", "||KEY SHIFT DOWN")
            self[f"BUS {i}||SLIDER GAIN"].bind("<Control-KeyPress-Up>", "||KEY CTRL UP")
            self[f"BUS {i}||SLIDER GAIN"].bind("<Control-KeyPress-Down>", "||KEY CTRL DOWN")

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
            match parsed_cmd := self.parser.match.parseString(event):
                case [[button], ["FOCUS", "IN"]]:
                    if values["Browse"]:
                        filepath = values["Browse"]
                        break
                    self.nvda.speak(button)
                case [[button], ["KEY", "ENTER"]]:
                    window.find_element_with_focus().click()
            self.logger.debug(f"parsed::{parsed_cmd}")
        window.close()
        if filepath:
            return Path(filepath)

    def popup_rename(self, message, title=None, tab=None):
        if tab == "Physical Strip":
            upper = self.kind.phys_in + 1
        elif tab == "Virtual Strip":
            upper = self.kind.virt_in + 1
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
            match parsed_cmd := self.parser.match.parseString(event):
                case ["Index"]:
                    val = values["Index"]
                    self.nvda.speak(f"Index {val}")
                case [[button], ["FOCUS", "IN"]]:
                    if button == "Index":
                        val = values["Index"]
                        self.nvda.speak(f"Index {val}")
                    else:
                        self.nvda.speak(button)
                case [[button], ["KEY", "ENTER"]]:
                    window.find_element_with_focus().click()
                case ["Ok"]:
                    data = values
                    break
            self.logger.debug(f"parsed::{parsed_cmd}")
        window.close()
        return data

    def popup_advanced_settings(self, title):
        def _make_buffering_frame() -> psg.Frame:
            buffer = [
                [
                    psg.ButtonMenu(
                        driver,
                        size=(14, 2),
                        menu_def=["", util.get_asio_samples_list(driver)],
                        key=f"BUFFER {driver}",
                    )
                    for driver in ("MME", "WDM", "KS", "ASIO")
                ],
            ]
            return psg.Frame("BUFFERING", buffer)

        layout = []
        steps = (_make_buffering_frame,)
        for step in steps:
            layout.append([step()])
        layout.append([psg.Button("Exit", size=(8, 2))])

        window = psg.Window(title, layout, finalize=True)
        buttonmenu_opts = {"takefocus": 1, "highlightthickness": 1}
        for driver in ("MME", "WDM", "KS", "ASIO"):
            window[f"BUFFER {driver}"].Widget.config(**buttonmenu_opts)
            window[f"BUFFER {driver}"].bind("<FocusIn>", "||FOCUS IN")
            window[f"BUFFER {driver}"].bind("<space>", "||KEY SPACE", propagate=False)
            window[f"BUFFER {driver}"].bind("<Return>", "||KEY ENTER", propagate=False)
        window["Exit"].bind("<FocusIn>", "||FOCUS IN")
        window["Exit"].bind("<Return>", "||KEY ENTER")
        while True:
            event, values = window.read()
            self.logger.debug(f"event::{event}")
            self.logger.debug(f"values::{values}")
            if event in (psg.WIN_CLOSED, "Exit"):
                break
            match parsed_cmd := self.parser.match.parseString(event):
                case ["BUFFER MME" | "BUFFER WDM" | "BUFFER KS" | "BUFFER ASIO"]:
                    if values[event] == "Default":
                        if "MME" in event:
                            val = 1024
                        elif "WDM" in event or "KS" in event:
                            val = 512
                        else:
                            val = 0
                    else:
                        val = int(values[event])
                    driver = event.split()[1]
                    self.vm.set(f"option.buffer.{driver.lower()}", val)
                    self.TKroot.after(200, self.nvda.speak, f"{driver} BUFFER {val if val else 'default'}")
                case [["BUFFER", driver], ["FOCUS", "IN"]]:
                    val = int(self.vm.get(f"option.buffer.{driver.lower()}"))
                    self.nvda.speak(f"{driver} BUFFER {val if val else 'default'}")
                case [["BUFFER", driver], ["KEY", "SPACE" | "ENTER"]]:
                    util.open_context_menu_for_buttonmenu(window, f"BUFFER {driver}")
                case [[button], ["FOCUS", "IN"]]:
                    self.nvda.speak(button)
                case [[button], ["KEY", "ENTER"]]:
                    window.find_element_with_focus().click()
            self.logger.debug(f"parsed::{parsed_cmd}")
        window.close()

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

            match parsed_cmd := self.parser.match.parseString(event):
                # Focus tabgroup
                case ["CTRL-TAB"] | ["CTRL-SHIFT-TAB"]:
                    self["tabgroup"].set_focus()
                    self.nvda.speak(f"{values['tabgroup']}")

                # Rename popups
                case ["F2:113"]:
                    tab = values["tabgroup"]
                    if tab in ("Physical Strip", "Virtual Strip", "Buses"):
                        data = self.popup_rename("Label", title=f"Rename {tab}", tab=tab)
                        if not data:  # cancel was pressed
                            continue
                        index = int(data["Index"]) - 1
                        match tab:
                            case "Physical Strip":
                                label = data.get("Edit", f"Hardware Input {index + 1}")
                                self.vm.strip[index].label = label
                                self[f"STRIP {index}||LABEL"].update(value=label)
                                self.cache["labels"][f"STRIP {index}||LABEL"] = label
                            case "Virtual Strip":
                                index += self.kind.phys_in
                                label = data.get("Edit", f"Virtual Input {index - self.kind.phys_in + 1}")
                                self.vm.strip[index].label = label
                                self[f"STRIP {index}||LABEL"].update(value=label)
                                self.cache["labels"][f"STRIP {index}||LABEL"] = label
                            case "Buses":
                                if index < self.kind.phys_out:
                                    label = data.get("Edit", f"Physical Bus {index + 1}")
                                else:
                                    label = data.get("Edit", f"Virtual Bus {index - self.kind.phys_out + 1}")
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
                        for i in (25, 50):  # for the benefit of the sliders
                            self.TKroot.after(i, self.on_pdirty)
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
                        self.logger.debug("settings.json was truncated")

                # Tabs
                case ["tabgroup"] | [["tabgroup"], ["FOCUS", "IN"]]:
                    if self.find_element_with_focus() is None:
                        self.nvda.speak(f"{values['tabgroup']}")
                case [["tabgroup"], tabname] | [["tabgroup"], tabname, ["FOCUS", "IN"]]:
                    if self.find_element_with_focus() is None:
                        name = " ".join(tabname)
                        self.nvda.speak(f"{values[f'tabgroup||{name}']}")
                case [["tabgroup"], _, ["KEY", "SHIFT", "TAB"]]:
                    self.nvda.speak(values["tabgroup"])

                # Hardware In
                case [["HARDWARE", "IN"], [key]]:
                    selection = values[f"HARDWARE IN||{key}"]
                    index = int(key) - 1
                    match selection.split(":"):
                        case [device_name]:
                            setattr(self.vm.strip[index].device, "wdm", "")
                            self.TKroot.after(200, self.nvda.speak, f"HARDWARE IN {key} device selection removed")
                        case [driver, device_name]:
                            setattr(self.vm.strip[index].device, driver, device_name.lstrip())
                            phonetic = {"mme": "em em e"}
                            self.TKroot.after(
                                200,
                                self.nvda.speak,
                                f"HARDWARE IN {key} set {phonetic.get(driver, driver)} {device_name}",
                            )
                case [["HARDWARE", "IN"], [key], ["FOCUS", "IN"]]:
                    if self.find_element_with_focus() is not None:
                        self.nvda.speak(f"HARDWARE INPUT {key} {self.cache['hw_ins'][f'HARDWARE IN||{key}']}")
                case [["HARDWARE", "IN"], [key], ["KEY", "SPACE" | "ENTER"]]:
                    util.open_context_menu_for_buttonmenu(self, f"HARDWARE IN||{key}")

                # Hardware out
                case [["HARDWARE", "OUT"], [key]]:
                    selection = values[f"HARDWARE OUT||{key}"]
                    index = int(key[1]) - 1
                    match selection.split(":"):
                        case [device_name]:
                            setattr(self.vm.bus[index].device, "wdm", "")
                            self.TKroot.after(200, self.nvda.speak, f"HARDWARE OUT {key} device selection removed")
                        case [driver, device_name]:
                            setattr(self.vm.bus[index].device, driver, device_name.lstrip())
                            phonetic = {"mme": "em em e"}
                            self.TKroot.after(
                                200,
                                self.nvda.speak,
                                f"HARDWARE OUT {key} set {phonetic.get(driver, driver)} {device_name}",
                            )
                case [["HARDWARE", "OUT"], [key], ["FOCUS", "IN"]]:
                    if self.find_element_with_focus() is not None:
                        self.nvda.speak(f"HARDWARE OUT {key} {self.cache['hw_outs'][f'HARDWARE OUT||{key}']}")
                case [["HARDWARE", "OUT"], [key], ["KEY", "SPACE" | "ENTER"]]:
                    util.open_context_menu_for_buttonmenu(self, f"HARDWARE OUT||{key}")

                # Patch ASIO
                case [["ASIO", "CHECKBOX"], [in_num, channel]]:
                    index = util.get_asio_checkbox_index(int(channel), int(in_num[-1]))
                    val = values[f"ASIO CHECKBOX||{in_num} {channel}"]
                    self.vm.patch.asio[index].set(val)
                    channel = ("left", "right")[int(channel)]
                    self.nvda.speak(f"Patch ASIO {in_num} {channel} set to {val}")
                case [["ASIO", "CHECKBOX"], [in_num, channel], ["FOCUS", "IN"]]:
                    if self.find_element_with_focus() is not None:
                        val = values[f"ASIO CHECKBOX||{in_num} {channel}"]
                        channel = ("left", "right")[int(channel)]
                        num = int(in_num[-1])
                        self.nvda.speak(f"Patch ASIO inputs to strips IN#{num} {channel} {val}")

                # Patch COMPOSITE
                case [["PATCH", "COMPOSITE"], [key]]:
                    val = values[f"PATCH COMPOSITE||{key}"]
                    index = int(key[-1]) - 1
                    self.vm.patch.composite[index].set(util.get_patch_composite_list(self.kind).index(val) + 1)
                    self.TKroot.after(200, self.nvda.speak, f"PATCH COMPOSITE {key[-1]} set {val}")
                case [["PATCH", "COMPOSITE"], [key], ["FOCUS", "IN"]]:
                    if self.find_element_with_focus() is not None:
                        if values[f"PATCH COMPOSITE||{key}"]:
                            val = values[f"PATCH COMPOSITE||{key}"]
                        else:
                            index = int(key[-1]) - 1
                            val = util.get_patch_composite_list(self.kind)[self.vm.patch.composite[index].get() - 1]
                        self.nvda.speak(f"Patch COMPOSITE {key[-1]} {val}")
                case [["PATCH", "COMPOSITE"], [key], ["KEY", "SPACE" | "ENTER"]]:
                    util.open_context_menu_for_buttonmenu(self, f"PATCH COMPOSITE||{key}")

                # Patch INSERT
                case [["INSERT", "CHECKBOX"], [in_num, channel]]:
                    index = util.get_insert_checkbox_index(
                        self.kind,
                        int(channel),
                        int(in_num[-1]),
                    )
                    val = values[f"INSERT CHECKBOX||{in_num} {channel}"]
                    self.vm.patch.insert[index].on = val
                    self.nvda.speak(
                        f"PATCH INSERT {in_num} {util._patch_insert_channels[int(channel)]} set to {'on' if val else 'off'}"
                    )
                case [["INSERT", "CHECKBOX"], [in_num, channel], ["FOCUS", "IN"]]:
                    if self.find_element_with_focus() is not None:
                        index = util.get_insert_checkbox_index(
                            self.kind,
                            int(channel),
                            int(in_num[-1]),
                        )
                        val = values[f"INSERT CHECKBOX||{in_num} {channel}"]
                        channel = util._patch_insert_channels[int(channel)]
                        num = int(in_num[-1])
                        self.nvda.speak(f"Patch INSERT IN#{num} {channel} {'on' if val else 'off'}")

                # Advanced Settings
                case ["ADVANCED SETTINGS"] | ["CTRL-A"]:
                    if values["tabgroup"] == "tab||Settings":
                        self.popup_advanced_settings(title="Advanced Settings")
                case [["ADVANCED", "SETTINGS"], ["FOCUS", "IN"]]:
                    self.nvda.speak("ADVANCED SETTINGS")
                case [["ADVANCED", "SETTINGS"], ["KEY", "ENTER"]]:
                    self.find_element_with_focus().click()

                # Strip Params
                case [["STRIP", index], [param]]:
                    label = self.cache["labels"][f"STRIP {index}||LABEL"]
                    match param:
                        case "MONO":
                            if int(index) < self.kind.phys_in:
                                actual = param.lower()
                            elif int(index) == self.kind.phys_in + 1:
                                actual = "k"
                            else:
                                actual = "mc"
                            phonetic = {"k": "karaoke"}
                            if actual == "k":
                                next_val = self.vm.strip[int(index)].k + 1
                                if next_val == 4:
                                    next_val = 0
                                setattr(self.vm.strip[int(index)], actual, next_val)
                                self.cache["strip"][f"STRIP {index}||{param}"] = next_val
                                self.nvda.speak(
                                    f"{label} {phonetic.get(actual, actual)} {['off', 'k m', 'k 1', 'k 2'][next_val]}"
                                )
                            else:
                                val = not self.cache["strip"][f"STRIP {index}||{param}"]
                                setattr(self.vm.strip[int(index)], actual, val)
                                self.cache["strip"][f"STRIP {index}||{param}"] = val
                                self.nvda.speak(f"{label} {phonetic.get(actual, actual)} {'on' if val else 'off'}")
                        case _:
                            val = not self.cache["strip"][f"STRIP {index}||{param}"]
                            setattr(self.vm.strip[int(index)], param if param[0] in ("A", "B") else param.lower(), val)
                            self.cache["strip"][f"STRIP {index}||{param}"] = val
                            self.nvda.speak(f"{label} {param} {'on' if val else 'off'}")
                case [["STRIP", index], [param], ["FOCUS", "IN"]]:
                    if self.find_element_with_focus() is not None:
                        val = self.cache["strip"][f"STRIP {index}||{param}"]
                        match param:
                            case "MONO":
                                if int(index) < self.kind.phys_in:
                                    actual = param.lower()
                                elif int(index) == self.kind.phys_in + 1:
                                    actual = "k"
                                else:
                                    actual = "mc"
                            case _:
                                actual = param
                        phonetic = {"k": "karaoke"}
                        label = self.cache["labels"][f"STRIP {index}||LABEL"]
                        if actual == "k":
                            self.nvda.speak(
                                f"{label} {phonetic.get(actual, actual)} {['off', 'k m', 'k 1', 'k 2'][self.cache['strip'][f'STRIP {int(index)}||{param}']]}"
                            )
                        else:
                            self.nvda.speak(f"{label} {phonetic.get(actual, actual)} {'on' if val else 'off'}")
                case [["STRIP", index], [param], ["KEY", "ENTER"]]:
                    self.find_element_with_focus().click()

                # Strip Sliders
                case [
                    ["STRIP", index],
                    [
                        "SLIDER",
                        "GAIN"
                        | "COMP"
                        | "GATE"
                        | "DENOISER"
                        | "AUDIBILITY"
                        | "LIMIT"
                        | "BASS"
                        | "MID"
                        | "TREBLE" as param,
                    ],
                ]:
                    label = self.cache["labels"][f"STRIP {index}||LABEL"]
                    val = values[event]
                    match param:
                        case "GAIN":
                            self.vm.strip[int(index)].gain = val
                        case "COMP" | "GATE" | "DENOISER":
                            target = getattr(self.vm.strip[int(index)], param.lower())
                            target.knob = val
                        case "AUDIBILITY":
                            self.vm.strip[int(index)].audibility = val
                        case "LIMIT":
                            val = int(val)
                            self.vm.strip[int(index)].limit = val
                        case "BASS" | "MID" | "TREBLE":
                            setattr(self.vm.strip[int(index)], param.lower(), val)
                    self.nvda.speak(f"{label} {param} slider {val}")
                case [
                    ["STRIP", index],
                    [
                        "SLIDER",
                        "GAIN"
                        | "COMP"
                        | "GATE"
                        | "DENOISER"
                        | "AUDIBILITY"
                        | "LIMIT"
                        | "BASS"
                        | "MID"
                        | "TREBLE" as param,
                    ],
                    ["FOCUS", "IN"],
                ]:
                    if self.find_element_with_focus() is not None:
                        self.vm.event.pdirty = False
                        label = self.cache["labels"][f"STRIP {index}||LABEL"]
                        val = values[f"STRIP {index}||SLIDER {param}"]
                        self.nvda.speak(f"{label} {param} slider {int(val) if param == 'LIMIT' else val}")
                case [
                    ["STRIP", index],
                    [
                        "SLIDER",
                        "GAIN" | "COMP" | "GATE" | "DENOISER" | "AUDIBILITY" | "LIMIT" | "BASS" | "MID" | "TREBLE",
                    ],
                    ["FOCUS", "OUT"],
                ]:
                    self.vm.event.pdirty = True
                case [
                    ["STRIP", index],
                    [
                        "SLIDER",
                        "GAIN"
                        | "COMP"
                        | "GATE"
                        | "DENOISER"
                        | "AUDIBILITY"
                        | "LIMIT"
                        | "BASS"
                        | "MID"
                        | "TREBLE" as param,
                    ],
                    ["KEY", "LEFT" | "RIGHT" | "UP" | "DOWN" as direction],
                ]:
                    match param:
                        case "GAIN":
                            val = self.vm.strip[int(index)].gain
                        case "COMP" | "GATE" | "DENOISER":
                            target = getattr(self.vm.strip[int(index)], param.lower())
                            val = target.knob
                        case "AUDIBILITY":
                            val = self.vm.strip[int(index)].audibility
                        case "BASS" | "MID" | "TREBLE":
                            val = getattr(self.vm.strip[int(index)], param.lower())
                        case "LIMIT":
                            val = self.vm.strip[int(index)].limit

                    match direction:
                        case "RIGHT" | "UP":
                            val += 1
                        case "LEFT" | "DOWN":
                            val -= 1

                    match param:
                        case "GAIN":
                            self.vm.strip[int(index)].gain = util.check_bounds(val, (-60, 12))
                            self[f"STRIP {index}||SLIDER {param}"].update(value=util.check_bounds(val, (-60, 12)))
                        case "COMP" | "GATE" | "DENOISER":
                            setattr(target, "knob", util.check_bounds(val, (0, 10)))
                            self[f"STRIP {index}||SLIDER {param}"].update(value=util.check_bounds(val, (0, 10)))
                        case "AUDIBILITY":
                            self.vm.strip[int(index)].audibility = util.check_bounds(val, (0, 10))
                            self[f"STRIP {index}||SLIDER {param}"].update(value=util.check_bounds(val, (0, 10)))
                        case "BASS" | "MID" | "TREBLE":
                            setattr(self.vm.strip[int(index)], param.lower(), util.check_bounds(val, (-12, 12)))
                            self[f"STRIP {index}||SLIDER {param}"].update(value=util.check_bounds(val, (-12, 12)))
                        case "LIMIT":
                            self.vm.strip[int(index)].limit = util.check_bounds(val, (-40, 12))
                            self[f"STRIP {index}||SLIDER {param}"].update(value=util.check_bounds(val, (-40, 12)))
                case [
                    ["STRIP", index],
                    [
                        "SLIDER",
                        "GAIN"
                        | "COMP"
                        | "GATE"
                        | "DENOISER"
                        | "AUDIBILITY"
                        | "LIMIT"
                        | "BASS"
                        | "MID"
                        | "TREBLE" as param,
                    ],
                    ["KEY", "CTRL", "LEFT" | "RIGHT" | "UP" | "DOWN" as direction],
                ]:
                    match param:
                        case "GAIN":
                            val = self.vm.strip[int(index)].gain
                        case "COMP" | "GATE" | "DENOISER":
                            target = getattr(self.vm.strip[int(index)], param.lower())
                            val = target.knob
                        case "AUDIBILITY":
                            val = self.vm.strip[int(index)].audibility
                        case "BASS" | "MID" | "TREBLE":
                            val = getattr(self.vm.strip[int(index)], param.lower())
                        case "LIMIT":
                            val = self.vm.strip[int(index)].limit

                    match direction:
                        case "RIGHT" | "UP":
                            if param in ("COMP", "GATE", "DENOISER", "AUDIBILITY", "BASS", "MID", "TREBLE"):
                                val += 1
                            else:
                                val += 3
                        case "LEFT" | "DOWN":
                            if param in ("COMP", "GATE", "DENOISER", "AUDIBILITY", "BASS", "MID", "TREBLE"):
                                val -= 1
                            else:
                                val -= 3

                    match param:
                        case "GAIN":
                            self.vm.strip[int(index)].gain = util.check_bounds(val, (-60, 12))
                            self[f"STRIP {index}||SLIDER {param}"].update(value=util.check_bounds(val, (-60, 12)))
                        case "COMP" | "GATE" | "DENOISER":
                            setattr(target, "knob", util.check_bounds(val, (0, 10)))
                            self[f"STRIP {index}||SLIDER {param}"].update(value=util.check_bounds(val, (0, 10)))
                        case "AUDIBILITY":
                            self.vm.strip[int(index)].audibility = util.check_bounds(val, (0, 10))
                            self[f"STRIP {index}||SLIDER {param}"].update(value=util.check_bounds(val, (0, 10)))
                        case "BASS" | "MID" | "TREBLE":
                            setattr(self.vm.strip[int(index)], param.lower(), util.check_bounds(val, (-12, 12)))
                            self[f"STRIP {index}||SLIDER {param}"].update(value=util.check_bounds(val, (-12, 12)))
                        case "LIMIT":
                            self.vm.strip[int(index)].limit = util.check_bounds(val, (-40, 12))
                            self[f"STRIP {index}||SLIDER {param}"].update(value=util.check_bounds(val, (-40, 12)))
                case [
                    ["STRIP", index],
                    [
                        "SLIDER",
                        "GAIN"
                        | "COMP"
                        | "GATE"
                        | "DENOISER"
                        | "AUDIBILITY"
                        | "LIMIT"
                        | "BASS"
                        | "MID"
                        | "TREBLE" as param,
                    ],
                    ["KEY", "SHIFT", "LEFT" | "RIGHT" | "UP" | "DOWN" as direction],
                ]:
                    match param:
                        case "GAIN":
                            val = self.vm.strip[int(index)].gain
                        case "COMP" | "GATE" | "DENOISER":
                            target = getattr(self.vm.strip[int(index)], param.lower())
                            val = target.knob
                        case "AUDIBILITY":
                            val = self.vm.strip[int(index)].audibility
                        case "BASS" | "MID" | "TREBLE":
                            val = getattr(self.vm.strip[int(index)], param.lower())
                        case "LIMIT":
                            val = self.vm.strip[int(index)].limit

                    match direction:
                        case "RIGHT" | "UP":
                            if param == "LIMIT":
                                val += 1
                            else:
                                val += 0.1
                        case "LEFT" | "DOWN":
                            if param == "LIMIT":
                                val -= 1
                            else:
                                val -= 0.1

                    match param:
                        case "GAIN":
                            self.vm.strip[int(index)].gain = util.check_bounds(val, (-60, 12))
                            self[f"STRIP {index}||SLIDER {param}"].update(value=util.check_bounds(val, (-60, 12)))
                        case "COMP" | "GATE" | "DENOISER":
                            setattr(target, "knob", util.check_bounds(val, (0, 10)))
                            self[f"STRIP {index}||SLIDER {param}"].update(value=util.check_bounds(val, (0, 10)))
                        case "AUDIBILITY":
                            self.vm.strip[int(index)].audibility = util.check_bounds(val, (0, 10))
                            self[f"STRIP {index}||SLIDER {param}"].update(value=util.check_bounds(val, (0, 10)))
                        case "BASS" | "MID" | "TREBLE":
                            setattr(self.vm.strip[int(index)], param.lower(), util.check_bounds(val, (-12, 12)))
                            self[f"STRIP {index}||SLIDER {param}"].update(value=util.check_bounds(val, (-12, 12)))
                        case "LIMIT":
                            self.vm.strip[int(index)].limit = util.check_bounds(val, (-40, 12))
                            self[f"STRIP {index}||SLIDER {param}"].update(value=util.check_bounds(val, (-40, 12)))

                # Bus Params
                case [["BUS", index], [param]]:
                    val = self.cache["bus"][event]
                    label = self.cache["labels"][f"BUS {index}||LABEL"]
                    match param:
                        case "EQ":
                            val = not val
                            self.vm.bus[int(index)].eq.on = val
                            self.cache["bus"][event] = val
                            self.TKroot.after(
                                200,
                                self.nvda.speak,
                                f"{label} bus {param} {'on' if val else 'off'}",
                            )
                        case "MONO" | "MUTE":
                            val = not val
                            setattr(self.vm.bus[int(index)], param.lower(), val)
                            self.cache["bus"][event] = val
                            self.TKroot.after(
                                200,
                                self.nvda.speak,
                                f"{label} bus {param} {'on' if val else 'off'}",
                            )
                        case "MODE":
                            bus_modes = util.get_bus_modes(self.vm)
                            next_index = bus_modes.index(val) + 1
                            if next_index == len(bus_modes):
                                next_index = 0
                            next_bus = bus_modes[next_index]
                            phonetic = {
                                "amix": "Mix Down A",
                                "bmix": "Mix Down B",
                                "repeat": "Stereo Repeat",
                                "tvmix": "Up Mix TV",
                                "upmix21": "Up Mix 2.1",
                                "upmix41": "Up Mix 4.1",
                                "upmix61": "Up Mix 6.1",
                                "centeronly": "Center Only",
                                "lfeonly": "Low Frequency Effect Only",
                                "rearonly": "Rear Only",
                            }
                            setattr(self.vm.bus[int(index)].mode, next_bus, True)
                            self.cache["bus"][event] = next_bus
                            self.TKroot.after(
                                200,
                                self.nvda.speak,
                                f"{label} bus mode {phonetic.get(next_bus, next_bus)}",
                            )
                case [["BUS", index], [param], ["FOCUS", "IN"]]:
                    if self.find_element_with_focus() is not None:
                        label = self.cache["labels"][f"BUS {index}||LABEL"]
                        val = self.cache["bus"][f"BUS {index}||{param}"]
                        if param == "MODE":
                            self.nvda.speak(f"{label} bus {param} {val}")
                        else:
                            self.nvda.speak(f"{label} bus {param} {'on' if val else 'off'}")
                case [["BUS", index], [param], ["KEY", "ENTER"]]:
                    self.find_element_with_focus().click()

                # Bus Sliders
                case [["BUS", index], ["SLIDER", "GAIN"]]:
                    label = self.cache["labels"][f"BUS {index}||LABEL"]
                    val = values[event]
                    self.vm.bus[int(index)].gain = val
                    self.nvda.speak(f"{label} gain slider {val}")
                case [["BUS", index], ["SLIDER", "GAIN"], ["FOCUS", "IN"]]:
                    if self.find_element_with_focus() is not None:
                        self.vm.event.pdirty = False
                        label = self.cache["labels"][f"BUS {index}||LABEL"]
                        val = values[f"BUS {index}||SLIDER GAIN"]
                        self.nvda.speak(f"{label} gain slider {val}")
                case [["BUS", index], ["SLIDER", "GAIN"], ["FOCUS", "OUT"]]:
                    self.vm.event.pdirty = True
                case [["BUS", index], ["SLIDER", "GAIN"], ["KEY", "LEFT" | "RIGHT" | "UP" | "DOWN" as direction]]:
                    val = self.vm.bus[int(index)].gain
                    match direction:
                        case "RIGHT" | "UP":
                            val += 1
                        case "LEFT" | "DOWN":
                            val -= 1
                    self.vm.bus[int(index)].gain = util.check_bounds(val, (-60, 12))
                    self[f"BUS {index}||SLIDER GAIN"].update(value=val)
                case [
                    ["BUS", index],
                    ["SLIDER", "GAIN"],
                    ["KEY", "CTRL", "LEFT" | "RIGHT" | "UP" | "DOWN" as direction],
                ]:
                    val = self.vm.bus[int(index)].gain
                    match direction:
                        case "RIGHT" | "UP":
                            val += 3
                        case "LEFT" | "DOWN":
                            val -= 3
                    self.vm.bus[int(index)].gain = util.check_bounds(val, (-60, 12))
                    self[f"BUS {index}||SLIDER GAIN"].update(value=val)
                case [
                    ["BUS", index],
                    ["SLIDER", "GAIN"],
                    ["KEY", "SHIFT", "LEFT" | "RIGHT" | "UP" | "DOWN" as direction],
                ]:
                    val = self.vm.bus[int(index)].gain
                    match direction:
                        case "RIGHT" | "UP":
                            val += 0.1
                        case "LEFT" | "DOWN":
                            val -= 0.1
                    self.vm.bus[int(index)].gain = util.check_bounds(val, (-60, 12))
                    self[f"BUS {index}||SLIDER GAIN"].update(value=val)

                # Unknown
                case _:
                    self.logger.debug(f"Unknown event {event}")
            self.logger.debug(f"parsed::{parsed_cmd}")


def request_window_object(kind_id, vm):
    NVDAVMWindow_cls = NVDAVMWindow
    return NVDAVMWindow_cls(f"Voicemeeter {kind_id.capitalize()} NVDA", vm)
