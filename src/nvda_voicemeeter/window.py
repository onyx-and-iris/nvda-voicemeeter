import json
import logging
from pathlib import Path

import PySimpleGUI as psg

from . import configuration, models, util
from .builder import Builder
from .nvda import Nvda
from .parser import Parser
from .popup import Popup

logger = logging.getLogger(__name__)

psg.theme(configuration.get("default_theme", "Dark Blue 3"))
if psg.theme() == "HighContrast":
    psg.set_options(font=("Arial", 14))


class NVDAVMWindow(psg.Window):
    """Represents the main window of the Voicemeeter NVDA application"""

    def __init__(self, title, vm):
        self.vm = vm
        self.kind = self.vm.kind
        self.logger = logger.getChild(type(self).__name__)
        self.logger.debug(f"loaded with theme: {psg.theme()}")
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
        self.popup = Popup(self)
        self.builder = Builder(self)
        layout = self.builder.run()
        super().__init__(title, layout, return_keyboard_events=False, finalize=True)
        buttonmenu_opts = {"takefocus": 1, "highlightthickness": 1}
        for i in range(self.kind.phys_in):
            self[f"HARDWARE IN||{i + 1}"].Widget.config(**buttonmenu_opts)
        for i in range(self.kind.phys_out):
            self[f"HARDWARE OUT||A{i + 1}"].Widget.config(**buttonmenu_opts)
        if self.kind.name == "basic":
            self["HARDWARE OUT||A2"].Widget.config(**buttonmenu_opts)
        if self.kind.name != "basic":
            [self[f"PATCH COMPOSITE||PC{i + 1}"].Widget.config(**buttonmenu_opts) for i in range(self.kind.composite)]
        slider_opts = {"takefocus": 1, "highlightthickness": 1}
        for i in range(self.kind.num_strip):
            for param in util.get_slider_params(i, self.kind):
                self[f"STRIP {i}||SLIDER {param}"].Widget.config(**slider_opts)
            self[f"STRIP {i}||SLIDER GAIN"].Widget.config(**slider_opts)
            if self.kind.name != "basic":
                self[f"STRIP {i}||SLIDER LIMIT"].Widget.config(**slider_opts)
        for i in range(self.kind.num_bus):
            self[f"BUS {i}||SLIDER GAIN"].Widget.config(**slider_opts)
            self[f"BUS {i}||MODE"].Widget.config(**buttonmenu_opts)

        self.register_events()
        self["tabgroup"].set_focus()

    def __enter__(self):
        settings_path = configuration.SETTINGS
        if settings_path.exists():
            try:
                defaultconfig = Path(configuration.get("default_config", ""))  # coerce the type
                if defaultconfig.is_file() and defaultconfig.exists():
                    self.vm.set("command.load", str(defaultconfig))
                    self.logger.debug(f"config {defaultconfig} loaded")
                    self.TKroot.after(
                        200,
                        self.nvda.speak,
                        f"config {defaultconfig.stem} has been loaded",
                    )
            except json.JSONDecodeError:
                self.logger.debug("no default_config in settings.json. silently continuing...")

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
            for param in util.get_slider_params(i, self.kind):
                if param in ("AUDIBILITY", "BASS", "MID", "TREBLE"):
                    val = getattr(self.vm.strip[i], param.lower())
                else:
                    target = getattr(self.vm.strip[i], param.lower())
                    val = target.knob
                self[f"STRIP {i}||SLIDER {param}"].update(value=val)
        for i in range(self.kind.num_bus):
            self[f"BUS {i}||SLIDER GAIN"].update(value=self.vm.bus[i].gain)
        if self.kind.name != "basic":
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
        self.bind("<F2>", "F2")

        # NAV
        self.bind("<Control-a>", "CTRL-A")
        for i in range(1, 10):
            self.bind(f"<Control-Key-{i}>", f"CTRL-{i}")
        for i in range(1, 10):
            self.bind(f"<Alt-Key-{i}>", f"ALT-{i}")
        self.bind("<Control-o>", "CTRL-O")
        self.bind("<Control-s>", "CTRL-S")
        self.bind("<Control-m>", "CTRL-M")

        self.bind("<Control-g>", "GAIN MODE")
        self.bind("<Control-b>", "BASS MODE")
        self.bind("<Control-i>", "MID MODE")
        self.bind("<Control-r>", "TREBLE MODE")
        if self.kind.name == "basic":
            self.bind("<Control-u>", "AUDIBILITY MODE")
        elif self.kind.name == "banana":
            self.bind("<Control-c>", "COMP MODE")
            self.bind("<Control-t>", "GATE MODE")
            self.bind("<Control-l>", "LIMIT MODE")
        else:
            self.bind("<Control-c>", "COMP MODE")
            self.bind("<Control-t>", "GATE MODE")
            self.bind("<Control-d>", "DENOISER MODE")
            self.bind("<Control-l>", "LIMIT MODE")
        self.bind("<Escape>", "ESCAPE")

        for event in ("KeyPress", "KeyRelease"):
            event_id = event.removeprefix("Key").upper()
            for direction in ("Left", "Right", "Up", "Down"):
                self.bind(f"<Alt-{event}-{direction}>", f"ALT {direction.upper()}||{event_id}")
                self.bind(f"<Alt-Shift-{event}-{direction}>", f"ALT SHIFT {direction.upper()}||{event_id}")
                self.bind(f"<Alt-Control-{event}-{direction}>", f"ALT CTRL {direction.upper()}||{event_id}")

        # Hardware In
        for i in range(self.kind.phys_in):
            self[f"HARDWARE IN||{i + 1}"].bind("<FocusIn>", "||FOCUS IN")
            self[f"HARDWARE IN||{i + 1}"].bind("<space>", "||KEY SPACE", propagate=False)
            self[f"HARDWARE IN||{i + 1}"].bind("<Return>", "||KEY ENTER", propagate=False)

        # Hardware Out
        for i in range(self.kind.phys_out):
            self[f"HARDWARE OUT||A{i + 1}"].bind("<FocusIn>", "||FOCUS IN")
            self[f"HARDWARE OUT||A{i + 1}"].bind("<space>", "||KEY SPACE", propagate=False)
            self[f"HARDWARE OUT||A{i + 1}"].bind("<Return>", "||KEY ENTER", propagate=False)
        if self.kind.name == "basic":
            self["HARDWARE OUT||A2"].bind("<FocusIn>", "||FOCUS IN")
            self["HARDWARE OUT||A2"].bind("<space>", "||KEY SPACE", propagate=False)
            self["HARDWARE OUT||A2"].bind("<Return>", "||KEY ENTER", propagate=False)

        # Patch Composite
        if self.kind.name != "basic":
            for i in range(self.kind.composite):
                self[f"PATCH COMPOSITE||PC{i + 1}"].bind("<FocusIn>", "||FOCUS IN")
                self[f"PATCH COMPOSITE||PC{i + 1}"].bind("<space>", "||KEY SPACE", propagate=False)
                self[f"PATCH COMPOSITE||PC{i + 1}"].bind("<Return>", "||KEY ENTER", propagate=False)

        # Patch Insert
        if self.kind.name != "basic":
            for i in range(self.kind.num_strip):
                if i < self.kind.phys_in:
                    self[f"INSERT CHECKBOX||IN{i + 1} 0"].bind("<FocusIn>", "||FOCUS IN")
                    self[f"INSERT CHECKBOX||IN{i + 1} 1"].bind("<FocusIn>", "||FOCUS IN")
                    self[f"INSERT CHECKBOX||IN{i + 1} 0"].bind("<Return>", "||KEY ENTER")
                    self[f"INSERT CHECKBOX||IN{i + 1} 1"].bind("<Return>", "||KEY ENTER")
                else:
                    [self[f"INSERT CHECKBOX||IN{i + 1} {j}"].bind("<FocusIn>", "||FOCUS IN") for j in range(8)]
                    [self[f"INSERT CHECKBOX||IN{i + 1} {j}"].bind("<Return>", "||KEY ENTER") for j in range(8)]

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
                if i == self.kind.phys_in + 1:
                    for param in ("KARAOKE", "SOLO", "MUTE"):
                        self[f"STRIP {i}||{param}"].bind("<FocusIn>", "||FOCUS IN")
                        self[f"STRIP {i}||{param}"].bind("<Return>", "||KEY ENTER")
                else:
                    for param in ("MC", "SOLO", "MUTE"):
                        self[f"STRIP {i}||{param}"].bind("<FocusIn>", "||FOCUS IN")
                        self[f"STRIP {i}||{param}"].bind("<Return>", "||KEY ENTER")

        # Strip Sliders
        for i in range(self.kind.num_strip):
            for param in util.get_full_slider_params(i, self.kind):
                self[f"STRIP {i}||SLIDER {param}"].bind("<FocusIn>", "||FOCUS IN")
                self[f"STRIP {i}||SLIDER {param}"].bind("<FocusOut>", "||FOCUS OUT")
                for event in ("KeyPress", "KeyRelease"):
                    event_id = event.removeprefix("Key").upper()
                    for direction in ("Left", "Right", "Up", "Down"):
                        self[f"STRIP {i}||SLIDER {param}"].bind(
                            f"<{event}-{direction}>", f"||KEY {direction.upper()} {event_id}"
                        )
                        self[f"STRIP {i}||SLIDER {param}"].bind(
                            f"<Shift-{event}-{direction}>", f"||KEY SHIFT {direction.upper()} {event_id}"
                        )
                        self[f"STRIP {i}||SLIDER {param}"].bind(
                            f"<Control-{event}-{direction}>", f"||KEY CTRL {direction.upper()} {event_id}"
                        )
                self[f"STRIP {i}||SLIDER {param}"].bind("<Control-Shift-KeyPress-R>", "||KEY CTRL SHIFT R")

        # Bus Params
        params = ["MONO", "EQ", "MUTE"]
        if self.kind.name == "basic":
            params.remove("EQ")
        for i in range(self.kind.num_bus):
            for param in params:
                self[f"BUS {i}||{param}"].bind("<FocusIn>", "||FOCUS IN")
                self[f"BUS {i}||{param}"].bind("<Return>", "||KEY ENTER")
            self[f"BUS {i}||MODE"].bind("<FocusIn>", "||FOCUS IN")
            self[f"BUS {i}||MODE"].bind("<space>", "||KEY SPACE", propagate=False)
            self[f"BUS {i}||MODE"].bind("<Return>", "||KEY ENTER", propagate=False)

        # Bus Sliders
        for i in range(self.kind.num_bus):
            self[f"BUS {i}||SLIDER GAIN"].bind("<FocusIn>", "||FOCUS IN")
            self[f"BUS {i}||SLIDER GAIN"].bind("<FocusOut>", "||FOCUS OUT")
            for event in ("KeyPress", "KeyRelease"):
                event_id = event.removeprefix("Key").upper()
                for direction in ("Left", "Right", "Up", "Down"):
                    self[f"BUS {i}||SLIDER GAIN"].bind(
                        f"<{event}-{direction}>", f"||KEY {direction.upper()} {event_id}"
                    )
                    self[f"BUS {i}||SLIDER GAIN"].bind(
                        f"<Shift-{event}-{direction}>", f"||KEY SHIFT {direction.upper()} {event_id}"
                    )
                    self[f"BUS {i}||SLIDER GAIN"].bind(
                        f"<Control-{event}-{direction}>", f"||KEY CTRL {direction.upper()} {event_id}"
                    )
            self[f"BUS {i}||SLIDER GAIN"].bind("<Control-Shift-KeyPress-R>", "||KEY CTRL SHIFT R")

    def run(self):
        """
        Parses the event string and matches it to events

        Main thread will shutdown once a close or exit event occurs
        """
        mode = None

        while True:
            event, values = self.read()
            self.logger.debug(f"event::{event}")
            self.logger.debug(f"values::{values}")
            if event in (psg.WIN_CLOSED, "Exit"):
                break
            elif event in util.get_slider_modes():
                mode = event
                self.nvda.speak(f"{mode} enabled")
                self.logger.debug(f"entered slider mode {mode}")
                continue
            elif event == "ESCAPE":
                if mode:
                    self.nvda.speak(f"{mode} disabled")
                    self.logger.debug(f"exited from slider mode {mode}")
                    mode = None
                continue

            match parsed_cmd := self.parser.match.parseString(event):
                # Slider mode
                case [["ALT", "LEFT" | "RIGHT" | "UP" | "DOWN" as direction], ["PRESS" | "RELEASE" as e]]:
                    if mode:
                        self.write_event_value(f"SLIDER MODE {direction}||{e}", mode.split()[0])
                case [
                    ["ALT", "SHIFT" | "CTRL" as modifier, "LEFT" | "RIGHT" | "UP" | "DOWN" as direction],
                    ["PRESS" | "RELEASE" as e],
                ]:
                    if mode:
                        self.write_event_value(f"SLIDER MODE {modifier} {direction}||{e}", mode.split()[0])

                # Focus tabgroup
                case ["CTRL-TAB"] | ["CTRL-SHIFT-TAB"]:
                    self["tabgroup"].set_focus()
                    self.nvda.speak(f"{values['tabgroup']}")

                # Quick Navigation
                case ["CTRL-1" | "CTRL-2" | "CTRL-3" | "CTRL-4" | "CTRL-5" | "CTRL-6" | "CTRL-7" | "CTRL-8" as bind]:
                    key, index = bind.split("-")
                    match values["tabgroup"]:
                        case "tab||Physical Strip":
                            if int(index) > self.kind.phys_in:
                                continue
                            self[f"STRIP {int(index) - 1}||A1"].set_focus()
                            if (
                                self.find_element_with_focus() is None
                                or self.find_element_with_focus().Key != f"STRIP {int(index) - 1}||A1"
                            ):
                                self[f"STRIP {int(index) - 1}||SLIDER GAIN"].set_focus()
                        case "tab||Virtual Strip":
                            index = int(index) + self.kind.phys_in
                            if index > self.kind.num_strip:
                                continue
                            self[f"STRIP {index - 1}||A1"].set_focus()
                            if (
                                self.find_element_with_focus() is None
                                or self.find_element_with_focus().Key != f"STRIP {int(index) - 1}||A1"
                            ):
                                self[f"STRIP {int(index) - 1}||SLIDER GAIN"].set_focus()
                        case "tab||Buses":
                            if int(index) > self.kind.num_bus:
                                continue
                            self[f"BUS {int(index) - 1}||MONO"].set_focus()
                            if (
                                self.find_element_with_focus() is None
                                or self.find_element_with_focus().Key != f"BUS {int(index) - 1}||MONO"
                            ):
                                self[f"BUS {int(index) - 1}||SLIDER GAIN"].set_focus()
                case ["ALT-1" | "ALT-2" | "ALT-3" | "ALT-4" | "ALT-5" | "ALT-6" | "ALT-7" | "ALT-8" as bind]:
                    if values["tabgroup"] not in ("tab||Physical Strip", "tab||Virtual Strip", "tab||Buses"):
                        continue
                    key, index = bind.split("-")
                    if int(index) > self.kind.phys_out + self.kind.virt_out:
                        continue
                    if focus := self.find_element_with_focus():
                        identifier, param = focus.Key.split("||")
                        if int(index) <= self.kind.phys_out:
                            self.write_event_value(f"{identifier}||A{int(index)}", None)
                        else:
                            self.write_event_value(f"{identifier}||B{int(index) - self.kind.phys_out}", None)
                case ["CTRL-O"]:
                    if values["tabgroup"] not in ("tab||Physical Strip", "tab||Virtual Strip", "tab||Buses"):
                        continue
                    if focus := self.find_element_with_focus():
                        identifier, param = focus.Key.split("||")
                        self.write_event_value(f"{identifier}||MONO", None)
                case ["CTRL-S"]:
                    if values["tabgroup"] not in ("tab||Physical Strip", "tab||Virtual Strip"):
                        continue
                    if focus := self.find_element_with_focus():
                        identifier, param = focus.Key.split("||")
                        self.write_event_value(f"{identifier}||SOLO", None)
                case ["CTRL-M"]:
                    if values["tabgroup"] not in ("tab||Physical Strip", "tab||Virtual Strip", "tab||Buses"):
                        continue
                    if focus := self.find_element_with_focus():
                        identifier, param = focus.Key.split("||")
                        self.write_event_value(f"{identifier}||MUTE", None)
                case [["SLIDER", "MODE", direction], ["PRESS" | "RELEASE" as e]]:
                    if values["tabgroup"] not in ("tab||Physical Strip", "tab||Virtual Strip", "tab||Buses"):
                        continue
                    param = values[event]
                    if focus := self.find_element_with_focus():
                        identifier, partial = focus.Key.split("||")
                        _, index = identifier.split()
                        if param in util.get_full_slider_params(int(index), self.kind):
                            if "SLIDER" not in partial:
                                self.write_event_value(f"{identifier}||SLIDER {param}||KEY {direction} {e}", None)
                case [
                    ["SLIDER", "MODE", "SHIFT" | "CTRL" as modifier, direction],
                    ["PRESS" | "RELEASE" as e],
                ]:
                    if values["tabgroup"] not in ("tab||Physical Strip", "tab||Virtual Strip", "tab||Buses"):
                        continue
                    param = values[event]
                    if focus := self.find_element_with_focus():
                        identifier, partial = focus.Key.split("||")
                        _, index = identifier.split()
                        if param in util.get_full_slider_params(int(index), self.kind):
                            if "SLIDER" not in partial:
                                self.write_event_value(
                                    f"{identifier}||SLIDER {param}||KEY {modifier} {direction} {e}", None
                                )

                # Rename popups
                case ["F2"]:
                    tab = values["tabgroup"].split("||")[1]
                    if tab in ("Physical Strip", "Virtual Strip", "Buses"):
                        if focus := self.find_element_with_focus():
                            identifier, partial = focus.Key.split("||")
                            _, index = identifier.split()
                            index = int(index)
                            data = self.popup.rename("Label", index, title="Rename", tab=tab)
                            if not data:  # cancel was pressed
                                continue
                            match tab:
                                case "Physical Strip":
                                    label = data.get("Edit", f"Hardware Input {int(index) + 1}")
                                    self.vm.strip[int(index)].label = label
                                    self[f"STRIP {index}||LABEL"].update(value=label)
                                    self.cache["labels"][f"STRIP {index}||LABEL"] = label
                                case "Virtual Strip":
                                    label = data.get("Edit", f"Virtual Input {int(index) + 1}")
                                    self.vm.strip[int(index)].label = label
                                    self[f"STRIP {index}||LABEL"].update(value=label)
                                    self.cache["labels"][f"STRIP {index}||LABEL"] = label
                                case "Buses":
                                    if index < self.kind.phys_out:
                                        label = data.get("Edit", f"Physical Bus {int(index) + 1}")
                                    else:
                                        label = data.get("Edit", f"Virtual Bus {int(index) - self.kind.phys_out + 1}")
                                    self.vm.bus[int(index)].label = label
                                    self[f"BUS {index}||LABEL"].update(value=label)
                                    self.cache["labels"][f"BUS {index}||LABEL"] = label

                # Advanced popups (settings, comp, gate)
                case ["CTRL-A"]:
                    match values["tabgroup"]:
                        case "tab||Settings":
                            self.write_event_value("ADVANCED SETTINGS", None)
                        case "tab||Physical Strip":
                            if values["tabgroup||Physical Strip"] == "tab||Physical Strip||sliders":
                                if focus := self.find_element_with_focus():
                                    identifier, partial = focus.key.split("||")
                                    _, index = identifier.split()
                                    match self.kind.name:
                                        case "potato":
                                            if "SLIDER COMP" in partial:
                                                self.popup.compressor(int(index), title="Advanced Compressor")
                                            elif "SLIDER GATE" in partial:
                                                self.popup.gate(int(index), title="Advanced Gate")

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
                    if filepath := self.popup.save_as(
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
                        configuration.set("default_config", str(filepath))
                        self.TKroot.after(
                            200,
                            self.nvda.speak,
                            f"config {filepath.stem} set as default on startup",
                        )
                    else:
                        configuration.delete("default_config")
                        self.logger.debug("default_config removed from settings.json")

                case [theme, ["MENU", "THEME"]]:
                    chosen = " ".join(theme)
                    if chosen == "Default":
                        chosen = "Dark Blue 3"
                    configuration.set("default_theme", chosen)
                    self.TKroot.after(
                        200,
                        self.nvda.speak,
                        f"theme {chosen} selected.",
                    )
                    self.logger.debug(f"theme {chosen} selected")

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

                # Patch COMPOSITE
                case [["PATCH", "COMPOSITE"], [key]]:
                    val = values[f"PATCH COMPOSITE||{key}"]
                    index = int(key[-1]) - 1
                    self.vm.patch.composite[index].set(util.get_patch_composite_list(self.kind).index(val) + 1)
                    self.TKroot.after(200, self.nvda.speak, val)
                case [["PATCH", "COMPOSITE"], [key], ["FOCUS", "IN"]]:
                    if self.find_element_with_focus() is not None:
                        if values[f"PATCH COMPOSITE||{key}"]:
                            val = values[f"PATCH COMPOSITE||{key}"]
                        else:
                            index = int(key[-1]) - 1
                            comp_index = self.vm.patch.composite[index].get()
                            comp_list = util.get_patch_composite_list(self.kind)
                            try:
                                val = comp_list[comp_index - 1]
                            except IndexError as e:
                                val = comp_list[-1]
                                self.logger.error(f"{type(e).__name__}: {e}")
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
                    self.nvda.speak("on" if val else "off")
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
                case [["INSERT", "CHECKBOX"], [in_num, channel], ["KEY", "ENTER"]]:
                    val = not values[f"INSERT CHECKBOX||{in_num} {channel}"]
                    self.write_event_value(f"INSERT CHECKBOX||{in_num} {channel}", val)

                # Advanced Settings
                case ["ADVANCED SETTINGS"]:
                    if values["tabgroup"] == "tab||Settings":
                        self.popup.advanced_settings(title="Advanced Settings")
                case [["ADVANCED", "SETTINGS"], ["FOCUS", "IN"]]:
                    self.nvda.speak("ADVANCED SETTINGS")
                case [["ADVANCED", "SETTINGS"], ["KEY", "ENTER"]]:
                    self.find_element_with_focus().click()

                # Strip Params
                case [["STRIP", index], [param]]:
                    match param:
                        case "KARAOKE":
                            opts = ["off", "k m", "k 1", "k 2", "k v"]
                            next_val = self.vm.strip[int(index)].k + 1
                            if next_val == len(opts):
                                next_val = 0
                            self.vm.strip[int(index)].k = next_val
                            self.cache["strip"][f"STRIP {index}||{param}"] = next_val
                            self.nvda.speak(opts[next_val])
                        case output if param in util._get_bus_assignments(self.kind):
                            val = not self.cache["strip"][f"STRIP {index}||{output}"]
                            setattr(self.vm.strip[int(index)], output, val)
                            self.cache["strip"][f"STRIP {index}||{output}"] = val
                            self.nvda.speak("on" if val else "off")
                        case _:
                            val = not self.cache["strip"][f"STRIP {index}||{param}"]
                            setattr(self.vm.strip[int(index)], param.lower(), val)
                            self.cache["strip"][f"STRIP {index}||{param}"] = val
                            self.nvda.speak("on" if val else "off")
                case [["STRIP", index], [param], ["FOCUS", "IN"]]:
                    if self.find_element_with_focus() is not None:
                        val = self.cache["strip"][f"STRIP {index}||{param}"]
                        phonetic = {"KARAOKE": "karaoke"}
                        label = self.cache["labels"][f"STRIP {index}||LABEL"]
                        if param == "KARAOKE":
                            self.nvda.speak(
                                f"{label} {phonetic.get(param, param)} {['off', 'k m', 'k 1', 'k 2', 'k v'][self.cache['strip'][f'STRIP {int(index)}||{param}']]}"
                            )
                        else:
                            self.nvda.speak(f"{label} {phonetic.get(param, param)} {'on' if val else 'off'}")
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
                        val = values[f"STRIP {index}||SLIDER {param}"]
                        label = self.cache["labels"][f"STRIP {index}||LABEL"]
                        self.nvda.speak(f"{label} {param} {int(val) if param == 'LIMIT' else val}")
                case [
                    ["STRIP", index],
                    [
                        "SLIDER",
                        "GAIN" | "COMP" | "GATE" | "DENOISER" | "AUDIBILITY" | "LIMIT" | "BASS" | "MID" | "TREBLE",
                    ],
                    ["FOCUS", "OUT"],
                ]:
                    pass
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
                    ["KEY", "LEFT" | "RIGHT" | "UP" | "DOWN" as direction, "PRESS" | "RELEASE" as e],
                ]:
                    if e == "PRESS":
                        self.vm.event.pdirty = False
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
                                val = util.check_bounds(val, (-60, 12))
                                self.vm.strip[int(index)].gain = val
                                self[f"STRIP {index}||SLIDER {param}"].update(value=val)
                            case "COMP" | "GATE" | "DENOISER":
                                val = util.check_bounds(val, (0, 10))
                                setattr(target, "knob", val)
                                self[f"STRIP {index}||SLIDER {param}"].update(value=val)
                            case "AUDIBILITY":
                                val = util.check_bounds(val, (0, 10))
                                self.vm.strip[int(index)].audibility = val
                                self[f"STRIP {index}||SLIDER {param}"].update(value=val)
                            case "BASS" | "MID" | "TREBLE":
                                val = util.check_bounds(val, (-12, 12))
                                setattr(self.vm.strip[int(index)], param.lower(), val)
                                self[f"STRIP {index}||SLIDER {param}"].update(value=val)
                            case "LIMIT":
                                val = util.check_bounds(val, (-40, 12))
                                self.vm.strip[int(index)].limit = val
                                self[f"STRIP {index}||SLIDER {param}"].update(value=val)
                        self.nvda.speak(str(round(val, 1)))
                    else:
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
                    ["KEY", "CTRL", "LEFT" | "RIGHT" | "UP" | "DOWN" as direction, "PRESS" | "RELEASE" as e],
                ]:
                    if e == "PRESS":
                        self.vm.event.pdirty = False
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
                                val = util.check_bounds(val, (-60, 12))
                                self.vm.strip[int(index)].gain = val
                                self[f"STRIP {index}||SLIDER {param}"].update(value=val)
                            case "COMP" | "GATE" | "DENOISER":
                                val = util.check_bounds(val, (0, 10))
                                setattr(target, "knob", val)
                                self[f"STRIP {index}||SLIDER {param}"].update(value=val)
                            case "AUDIBILITY":
                                val = util.check_bounds(val, (0, 10))
                                self.vm.strip[int(index)].audibility = val
                                self[f"STRIP {index}||SLIDER {param}"].update(value=val)
                            case "BASS" | "MID" | "TREBLE":
                                val = util.check_bounds(val, (-12, 12))
                                setattr(self.vm.strip[int(index)], param.lower(), val)
                                self[f"STRIP {index}||SLIDER {param}"].update(value=val)
                            case "LIMIT":
                                val = util.check_bounds(val, (-40, 12))
                                self.vm.strip[int(index)].limit = val
                                self[f"STRIP {index}||SLIDER {param}"].update(value=val)
                        if param == "LIMIT":
                            self.nvda.speak(str(int(val)))
                        else:
                            self.nvda.speak(str(round(val, 1)))
                    else:
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
                    ["KEY", "SHIFT", "LEFT" | "RIGHT" | "UP" | "DOWN" as direction, "PRESS" | "RELEASE" as e],
                ]:
                    if e == "PRESS":
                        self.vm.event.pdirty = False
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
                                val = util.check_bounds(val, (-60, 12))
                                self.vm.strip[int(index)].gain = val
                                self[f"STRIP {index}||SLIDER {param}"].update(value=val)
                            case "COMP" | "GATE" | "DENOISER":
                                val = util.check_bounds(val, (0, 10))
                                setattr(target, "knob", val)
                                self[f"STRIP {index}||SLIDER {param}"].update(value=val)
                            case "AUDIBILITY":
                                val = util.check_bounds(val, (0, 10))
                                self.vm.strip[int(index)].audibility = val
                                self[f"STRIP {index}||SLIDER {param}"].update(value=val)
                            case "BASS" | "MID" | "TREBLE":
                                val = util.check_bounds(val, (-12, 12))
                                setattr(self.vm.strip[int(index)], param.lower(), val)
                                self[f"STRIP {index}||SLIDER {param}"].update(value=val)
                            case "LIMIT":
                                val = util.check_bounds(val, (-40, 12))
                                self.vm.strip[int(index)].limit = val
                                self[f"STRIP {index}||SLIDER {param}"].update(value=val)
                        if param == "LIMIT":
                            self.nvda.speak(str(int(val)))
                        else:
                            self.nvda.speak(str(round(val, 1)))
                    else:
                        self.vm.event.pdirty = True
                case [["STRIP", index], ["SLIDER", param], ["KEY", "CTRL", "SHIFT", "R"]]:
                    match param:
                        case "GAIN":
                            self.vm.strip[int(index)].gain = 0
                            self[f"STRIP {index}||SLIDER {param}"].update(value=0)
                        case "COMP" | "GATE" | "DENOISER":
                            target = getattr(self.vm.strip[int(index)], param.lower())
                            setattr(target, "knob", 0)
                            self[f"STRIP {index}||SLIDER {param}"].update(value=0)
                        case "AUDIBILITY":
                            self.vm.strip[int(index)].audibility = 0
                            self[f"STRIP {index}||SLIDER {param}"].update(value=0)
                        case "BASS" | "MID" | "TREBLE":
                            setattr(self.vm.strip[int(index)], param.lower(), 0)
                            self[f"STRIP {index}||SLIDER {param}"].update(value=0)
                        case "LIMIT":
                            self.vm.strip[int(index)].limit = 12
                            self[f"STRIP {index}||SLIDER {param}"].update(value=12)
                    self.nvda.speak(f"{12 if param == 'LIMIT' else 0}")

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
                                "on" if val else "off",
                            )
                        case "MONO" | "MUTE":
                            val = not val
                            setattr(self.vm.bus[int(index)], param.lower(), val)
                            self.cache["bus"][event] = val
                            self.TKroot.after(
                                200,
                                self.nvda.speak,
                                "on" if val else "off",
                            )
                        case "MODE":
                            chosen = util._bus_mode_map_reversed[values[event]]
                            setattr(self.vm.bus[int(index)].mode, chosen, True)
                            self.cache["bus"][event] = chosen
                            self.TKroot.after(
                                200,
                                self.nvda.speak,
                                util._bus_mode_map[chosen],
                            )
                case [["BUS", index], [param], ["FOCUS", "IN"]]:
                    if self.find_element_with_focus() is not None:
                        label = self.cache["labels"][f"BUS {index}||LABEL"]
                        val = self.cache["bus"][f"BUS {index}||{param}"]
                        if param == "MODE":
                            self.nvda.speak(f"{label} bus {param} {util._bus_mode_map[val]}")
                        else:
                            self.nvda.speak(f"{label} {param} {'on' if val else 'off'}")
                case [["BUS", index], [param], ["KEY", "SPACE" | "ENTER"]]:
                    if param == "MODE":
                        util.open_context_menu_for_buttonmenu(self, f"BUS {index}||MODE")
                    else:
                        self.find_element_with_focus().click()

                # Bus Sliders
                case [["BUS", index], ["SLIDER", "GAIN"]]:
                    label = self.cache["labels"][f"BUS {index}||LABEL"]
                    val = values[event]
                    self.vm.bus[int(index)].gain = val
                case [["BUS", index], ["SLIDER", "GAIN"], ["FOCUS", "IN"]]:
                    if self.find_element_with_focus() is not None:
                        label = self.cache["labels"][f"BUS {index}||LABEL"]
                        val = values[f"BUS {index}||SLIDER GAIN"]
                        self.nvda.speak(f"{label} gain {val}")
                case [["BUS", index], ["SLIDER", "GAIN"], ["FOCUS", "OUT"]]:
                    pass
                case [
                    ["BUS", index],
                    ["SLIDER", "GAIN"],
                    ["KEY", "LEFT" | "RIGHT" | "UP" | "DOWN" as direction, "PRESS" | "RELEASE" as e],
                ]:
                    if e == "PRESS":
                        self.vm.event.pdirty = False
                        val = self.vm.bus[int(index)].gain
                        match direction:
                            case "RIGHT" | "UP":
                                val += 1
                            case "LEFT" | "DOWN":
                                val -= 1
                        val = util.check_bounds(val, (-60, 12))
                        self.vm.bus[int(index)].gain = val
                        self[f"BUS {index}||SLIDER GAIN"].update(value=val)
                        self.nvda.speak(str(round(val, 1)))
                    else:
                        self.vm.event.pdirty = True
                case [
                    ["BUS", index],
                    ["SLIDER", "GAIN"],
                    ["KEY", "CTRL", "LEFT" | "RIGHT" | "UP" | "DOWN" as direction, "PRESS" | "RELEASE" as e],
                ]:
                    if e == "PRESS":
                        self.vm.event.pdirty = False
                        val = self.vm.bus[int(index)].gain
                        match direction:
                            case "RIGHT" | "UP":
                                val += 3
                            case "LEFT" | "DOWN":
                                val -= 3
                        val = util.check_bounds(val, (-60, 12))
                        self.vm.bus[int(index)].gain = val
                        self[f"BUS {index}||SLIDER GAIN"].update(value=val)
                        self.nvda.speak(str(round(val, 1)))
                    else:
                        self.vm.event.pdirty = True
                case [
                    ["BUS", index],
                    ["SLIDER", "GAIN"],
                    ["KEY", "SHIFT", "LEFT" | "RIGHT" | "UP" | "DOWN" as direction, "PRESS" | "RELEASE" as e],
                ]:
                    if e == "PRESS":
                        self.vm.event.pdirty = False
                        val = self.vm.bus[int(index)].gain
                        match direction:
                            case "RIGHT" | "UP":
                                val += 0.1
                            case "LEFT" | "DOWN":
                                val -= 0.1
                        val = util.check_bounds(val, (-60, 12))
                        self.vm.bus[int(index)].gain = val
                        self[f"BUS {index}||SLIDER GAIN"].update(value=val)
                        self.nvda.speak(str(round(val, 1)))
                    else:
                        self.vm.event.pdirty = True
                case [["BUS", index], ["SLIDER", "GAIN"], ["KEY", "CTRL", "SHIFT", "R"]]:
                    self.vm.bus[int(index)].gain = 0
                    self[f"BUS {index}||SLIDER GAIN"].update(value=0)
                    self.nvda.speak(str(0))

                # Unknown
                case _:
                    self.logger.debug(f"Unknown event {event}")
            self.logger.debug(f"parsed::{parsed_cmd}")


def request_window_object(kind_id, vm):
    NVDAVMWindow_cls = NVDAVMWindow
    return NVDAVMWindow_cls(f"Voicemeeter {kind_id.capitalize()} NVDA", vm)
