import logging
from pathlib import Path

import PySimpleGUI as psg

from . import util
from .compound import CompSlider, GateSlider, LabelSliderAdvanced

logger = logging.getLogger(__name__)


class Popup:
    def __init__(self, window):
        self.window = window
        self.kind = self.window.kind
        self.logger = logger.getChild(type(self).__name__)

    def save_as(self, message, title=None, initial_folder=None):
        layout = [
            [psg.Text(message)],
            [
                psg.FileSaveAs("Browse", initial_folder=str(initial_folder), file_types=(("XML", ".xml"),)),
                psg.Button("Cancel"),
            ],
        ]
        popup = psg.Window(title, layout, finalize=True)
        popup["Browse"].bind("<FocusIn>", "||FOCUS IN")
        popup["Browse"].bind("<Return>", "||KEY ENTER")
        popup["Cancel"].bind("<FocusIn>", "||FOCUS IN")
        popup["Cancel"].bind("<Return>", "||KEY ENTER")
        filepath = None
        while True:
            event, values = popup.read()
            self.logger.debug(f"event::{event}")
            self.logger.debug(f"values::{values}")
            if event in (psg.WIN_CLOSED, "Cancel"):
                break
            match parsed_cmd := self.window.parser.match.parseString(event):
                case [[button], ["FOCUS", "IN"]]:
                    if values["Browse"]:
                        filepath = values["Browse"]
                        break
                    self.window.nvda.speak(button)
                case [_, ["KEY", "ENTER"]]:
                    popup.find_element_with_focus().click()
            self.logger.debug(f"parsed::{parsed_cmd}")
        popup.close()
        if filepath:
            return Path(filepath)

    def on_pdirty(self):
        if self.popup.Title == "Advanced Settings":
            if self.kind.name != "basic":
                for key, value in self.window.cache["asio"].items():
                    if "INPUT" in key:
                        identifier, i = key.split("||")
                        partial = util.get_channel_identifier_list(self.window.vm)[int(i)]
                        self.popup[f"{identifier}||{partial}"].update(value=value)
                    elif "OUTPUT" in key:
                        self.popup[key].update(value=value)

        if self.popup.Title == "Advanced Compressor":
            for param in ("RATIO", "THRESHOLD", "ATTACK", "RELEASE", "KNEE"):
                self.popup[f"COMPRESSOR||SLIDER {param}"].update(
                    value=getattr(self.window.vm.strip[self.index].comp, param.lower())
                )
            self.popup["COMPRESSOR||SLIDER INPUT GAIN"].update(value=self.window.vm.strip[self.index].comp.gainin)
            self.popup["COMPRESSOR||SLIDER OUTPUT GAIN"].update(value=self.window.vm.strip[self.index].comp.gainout)
        elif self.popup.Title == "Advanced Gate":
            for param in ("THRESHOLD", "DAMPING", "BPSIDECHAIN", "ATTACK", "HOLD", "RELEASE"):
                self.popup[f"GATE||SLIDER {param}"].update(
                    value=getattr(self.window.vm.strip[self.index].gate, param.lower())
                )

    def rename(self, message, index, title=None, tab=None):
        if "Strip" in tab:
            if index < self.kind.phys_in:
                title += f" Physical Strip {index + 1}"
            else:
                title += f" Virtual Strip {index - self.kind.phys_in + 1}"
        else:
            if index < self.kind.phys_out:
                title += f" Physical Bus {index + 1}"
            else:
                title += f" Virtual Bus {index - self.kind.phys_out + 1}"
        layout = [
            [psg.Text(message)],
            [
                [
                    psg.Input(key="Edit"),
                ],
                [psg.Button("Ok"), psg.Button("Cancel")],
            ],
        ]
        popup = psg.Window(title, layout, finalize=True)
        popup["Edit"].bind("<FocusIn>", "||FOCUS IN")
        popup["Ok"].bind("<FocusIn>", "||FOCUS IN")
        popup["Ok"].bind("<Return>", "||KEY ENTER")
        popup["Cancel"].bind("<FocusIn>", "||FOCUS IN")
        popup["Cancel"].bind("<Return>", "||KEY ENTER")
        data = {}
        while True:
            event, values = popup.read()
            self.logger.debug(f"event::{event}")
            self.logger.debug(f"values::{values}")
            if event in (psg.WIN_CLOSED, "Cancel"):
                break
            match parsed_cmd := self.window.parser.match.parseString(event):
                case [[button], ["FOCUS", "IN"]]:
                    self.window.nvda.speak(button)
                case [_, ["KEY", "ENTER"]]:
                    popup.find_element_with_focus().click()
                case ["Ok"]:
                    data = values
                    break
            self.logger.debug(f"parsed::{parsed_cmd}")
        popup.close()
        return data

    def advanced_settings(self, title):
        def add_patch_asio_input_to_strips(layout, i):
            nums = list(range(99))
            layout.append(
                [
                    psg.Spin(
                        nums,
                        initial_value=self.window.cache["asio"][
                            f"ASIO INPUT SPINBOX||{util.get_asio_input_spinbox_index(0, i)}"
                        ],
                        size=2,
                        enable_events=True,
                        key=f"ASIO INPUT SPINBOX||IN{i} 0",
                    )
                ],
            )
            layout.append(
                [
                    psg.Spin(
                        nums,
                        initial_value=self.window.cache["asio"][
                            f"ASIO INPUT SPINBOX||{util.get_asio_input_spinbox_index(1, i)}"
                        ],
                        size=2,
                        enable_events=True,
                        key=f"ASIO INPUT SPINBOX||IN{i} 1",
                    )
                ],
            )

        def add_patch_bus_to_asio_outputs(layout, i):
            nums = list(range(99))
            layout.append(
                [
                    psg.Spin(
                        nums,
                        initial_value=self.window.cache["asio"][f"ASIO OUTPUT A{i} SPINBOX||{j}"],
                        size=2,
                        enable_events=True,
                        key=f"ASIO OUTPUT A{i} SPINBOX||{j}",
                    )
                    for j in range(self.kind.num_bus)
                ],
            )

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
        if self.kind.name != "basic":
            inner = []
            patch_input_to_strips = ([] for _ in range(self.kind.phys_in))
            for i, checkbox_list in enumerate(patch_input_to_strips):
                [step(checkbox_list, i + 1) for step in (add_patch_asio_input_to_strips,)]
                inner.append(psg.Frame(f"In#{i + 1}", checkbox_list))
            layout.append([psg.Frame("PATCH ASIO Inputs to Strips", [inner])])

            inner_2 = []
            patch_output_to_bus = ([] for _ in range(self.kind.phys_out - 1))
            for i, checkbox_list in enumerate(patch_output_to_bus):
                [step(checkbox_list, i + 2) for step in (add_patch_bus_to_asio_outputs,)]
                inner_2.append([psg.Frame(f"OutA{i + 2}", checkbox_list)])
            layout.append([psg.Frame("PATCH BUS to A1 ASIO Outputs", [*inner_2])])

        steps = (_make_buffering_frame,)
        for step in steps:
            layout.append([step()])
        layout.append([psg.Button("Exit", size=(8, 2))])

        self.popup = psg.Window(title, layout, finalize=True)
        if self.kind.name != "basic":
            for i in range(self.kind.phys_out):
                self.popup[f"ASIO INPUT SPINBOX||IN{i + 1} 0"].Widget.config(state="readonly")
                self.popup[f"ASIO INPUT SPINBOX||IN{i + 1} 1"].Widget.config(state="readonly")
            for i in range(self.kind.phys_out - 1):
                for j in range(self.kind.num_bus):
                    self.popup[f"ASIO OUTPUT A{i + 2} SPINBOX||{j}"].Widget.config(state="readonly")
        if self.kind.name != "basic":
            for i in range(self.kind.phys_out):
                self.popup[f"ASIO INPUT SPINBOX||IN{i + 1} 0"].bind("<FocusIn>", "||FOCUS IN")
                self.popup[f"ASIO INPUT SPINBOX||IN{i + 1} 1"].bind("<FocusIn>", "||FOCUS IN")
            for i in range(self.kind.phys_out - 1):
                for j in range(self.kind.num_bus):
                    self.popup[f"ASIO OUTPUT A{i + 2} SPINBOX||{j}"].bind("<FocusIn>", "||FOCUS IN")
        buttonmenu_opts = {"takefocus": 1, "highlightthickness": 1}
        for driver in ("MME", "WDM", "KS", "ASIO"):
            self.popup[f"BUFFER {driver}"].Widget.config(**buttonmenu_opts)
            self.popup[f"BUFFER {driver}"].bind("<FocusIn>", "||FOCUS IN")
            self.popup[f"BUFFER {driver}"].bind("<space>", "||KEY SPACE", propagate=False)
            self.popup[f"BUFFER {driver}"].bind("<Return>", "||KEY ENTER", propagate=False)
        self.popup["Exit"].bind("<FocusIn>", "||FOCUS IN")
        self.popup["Exit"].bind("<Return>", "||KEY ENTER")
        self.window.vm.observer.add(self.on_pdirty)
        while True:
            event, values = self.popup.read()
            self.logger.debug(f"event::{event}")
            self.logger.debug(f"values::{values}")
            if event in (psg.WIN_CLOSED, "Exit"):
                break
            match parsed_cmd := self.window.parser.match.parseString(event):
                case [["ASIO", "INPUT", "SPINBOX"], [in_num, channel]]:
                    index = util.get_asio_input_spinbox_index(int(channel), int(in_num[-1]))
                    val = values[f"ASIO INPUT SPINBOX||{in_num} {channel}"]
                    self.window.vm.patch.asio[index].set(val)
                    channel = ("left", "right")[int(channel)]
                    self.window.nvda.speak(str(val))
                case [["ASIO", "INPUT", "SPINBOX"], [in_num, channel], ["FOCUS", "IN"]]:
                    if self.popup.find_element_with_focus() is not None:
                        val = values[f"ASIO INPUT SPINBOX||{in_num} {channel}"]
                        channel = ("left", "right")[int(channel)]
                        num = int(in_num[-1])
                        self.window.nvda.speak(f"Patch ASIO inputs to strips IN#{num} {channel} {val}")
                case [["ASIO", "OUTPUT", param, "SPINBOX"], [index]]:
                    target = getattr(self.window.vm.patch, param)[int(index)]
                    target.set(values[event])
                    self.window.nvda.speak(str(values[event]))
                case [["ASIO", "OUTPUT", param, "SPINBOX"], [index], ["FOCUS", "IN"]]:
                    if self.popup.find_element_with_focus() is not None:
                        val = values[f"ASIO OUTPUT {param} SPINBOX||{index}"]
                        self.window.nvda.speak(
                            f"Patch BUS to A1 ASIO Outputs OUT {param} channel {int(index) + 1} {val}"
                        )
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
                    self.window.vm.set(f"option.buffer.{driver.lower()}", val)
                    self.window.TKroot.after(
                        200, self.window.nvda.speak, f"{driver} BUFFER {val if val else 'default'}"
                    )
                case [["BUFFER", driver], ["FOCUS", "IN"]]:
                    val = int(self.window.vm.get(f"option.buffer.{driver.lower()}"))
                    self.window.nvda.speak(f"{driver} BUFFER {val if val else 'default'}")
                case [["BUFFER", driver], ["KEY", "SPACE" | "ENTER"]]:
                    util.open_context_menu_for_buttonmenu(self.popup, f"BUFFER {driver}")
                case [[button], ["FOCUS", "IN"]]:
                    self.window.nvda.speak(button)
                case [_, ["KEY", "ENTER"]]:
                    self.popup.find_element_with_focus().click()
            self.logger.debug(f"parsed::{parsed_cmd}")
        self.window.vm.observer.remove(self.on_pdirty)
        self.popup.close()

    def compressor(self, index, title=None):
        self.index = index

        def _make_comp_frame() -> psg.Frame:
            comp_layout = [
                [LabelSliderAdvanced(self.window, index, param, CompSlider)]
                for param in ("INPUT GAIN", "RATIO", "THRESHOLD", "ATTACK", "RELEASE", "KNEE", "OUTPUT GAIN")
            ]
            return psg.Frame("ADVANCED COMPRESSOR", comp_layout)

        layout = []
        steps = (_make_comp_frame,)
        for step in steps:
            layout.append([step()])
        layout.append([psg.Button("MAKEUP", size=(12, 1)), psg.Button("Exit", size=(8, 1))])

        self.popup = psg.Window(title, layout, return_keyboard_events=False, finalize=True)
        buttonmenu_opts = {"takefocus": 1, "highlightthickness": 1}
        for param in ("INPUT GAIN", "RATIO", "THRESHOLD", "ATTACK", "RELEASE", "KNEE", "OUTPUT GAIN"):
            self.popup[f"COMPRESSOR||SLIDER {param}"].Widget.config(**buttonmenu_opts)
            self.popup[f"COMPRESSOR||SLIDER {param}"].bind("<FocusIn>", "||FOCUS IN")
            self.popup[f"COMPRESSOR||SLIDER {param}"].bind("<FocusOut>", "||FOCUS OUT")
            for event in ("KeyPress", "KeyRelease"):
                event_id = event.removeprefix("Key").upper()
                for direction in ("Left", "Right", "Up", "Down"):
                    self.popup[f"COMPRESSOR||SLIDER {param}"].bind(
                        f"<{event}-{direction}>", f"||KEY {direction.upper()} {event_id}"
                    )
                    self.popup[f"COMPRESSOR||SLIDER {param}"].bind(
                        f"<Shift-{event}-{direction}>", f"||KEY SHIFT {direction.upper()} {event_id}"
                    )
                    self.popup[f"COMPRESSOR||SLIDER {param}"].bind(
                        f"<Control-{event}-{direction}>", f"||KEY CTRL {direction.upper()} {event_id}"
                    )
                    if param == "RELEASE":
                        self.popup[f"COMPRESSOR||SLIDER {param}"].bind(
                            f"<Alt-{event}-{direction}>", f"||KEY ALT {direction.upper()} {event_id}"
                        )
                        self.popup[f"COMPRESSOR||SLIDER {param}"].bind(
                            f"<Control-Alt-{event}-{direction}>", f"||KEY CTRL ALT {direction.upper()} {event_id}"
                        )
            self.popup[f"COMPRESSOR||SLIDER {param}"].bind("<Control-Shift-KeyPress-R>", "||KEY CTRL SHIFT R")
        self.popup["MAKEUP"].bind("<FocusIn>", "||FOCUS IN")
        self.popup["MAKEUP"].bind("<Return>", "||KEY ENTER")
        self.popup["Exit"].bind("<FocusIn>", "||FOCUS IN")
        self.popup["Exit"].bind("<Return>", "||KEY ENTER")
        self.window.vm.observer.add(self.on_pdirty)
        while True:
            event, values = self.popup.read()
            self.logger.debug(f"event::{event}")
            self.logger.debug(f"values::{values}")
            if event in (psg.WIN_CLOSED, "Exit"):
                break
            match parsed_cmd := self.window.parser.match.parseString(event):
                case [["COMPRESSOR"], ["SLIDER", param]]:
                    setattr(self.window.vm.strip[index].comp, param.lower(), values[event])
                case [["COMPRESSOR"], ["SLIDER", param], ["FOCUS", "IN"]]:
                    self.window.nvda.speak(f"{param} {values[f'COMPRESSOR||SLIDER {param}']}")
                case [
                    ["COMPRESSOR"],
                    ["SLIDER", param],
                    ["KEY", "LEFT" | "RIGHT" | "UP" | "DOWN" as input_direction, "PRESS" | "RELEASE" as e],
                ]:
                    if e == "PRESS":
                        self.window.vm.event.pdirty = False
                        val = getattr(self.window.vm.strip[index].comp, param.lower())

                        match input_direction:
                            case "RIGHT" | "UP":
                                if param == "KNEE":
                                    val += 0.1
                                else:
                                    val += 1
                            case "LEFT" | "DOWN":
                                if param == "KNEE":
                                    val -= 0.1
                                else:
                                    val -= 1

                        val = CompSlider.check_bounds(param, val)

                        setattr(self.window.vm.strip[index].comp, param.lower(), val)
                        self.popup[f"COMPRESSOR||SLIDER {param}"].update(value=val)
                        if param == "KNEE":
                            self.window.nvda.speak(str(round(val, 2)))
                        else:
                            self.window.nvda.speak(str(round(val, 1)))
                    else:
                        self.window.vm.event.pdirty = True
                case [
                    ["COMPRESSOR"],
                    ["SLIDER", param],
                    ["KEY", "CTRL", "LEFT" | "RIGHT" | "UP" | "DOWN" as input_direction, "PRESS" | "RELEASE" as e],
                ]:
                    if e == "PRESS":
                        self.window.vm.event.pdirty = False
                        val = getattr(self.window.vm.strip[index].comp, param.lower())

                        match input_direction:
                            case "RIGHT" | "UP":
                                if param == "KNEE":
                                    val += 0.3
                                elif param == "RELEASE":
                                    val += 5
                                else:
                                    val += 3
                            case "LEFT" | "DOWN":
                                if param == "KNEE":
                                    val -= 0.3
                                elif param == "RELEASE":
                                    val -= 5
                                else:
                                    val -= 3

                        val = CompSlider.check_bounds(param, val)

                        setattr(self.window.vm.strip[index].comp, param.lower(), val)
                        self.popup[f"COMPRESSOR||SLIDER {param}"].update(value=val)
                        if param == "KNEE":
                            self.window.nvda.speak(str(round(val, 2)))
                        else:
                            self.window.nvda.speak(str(round(val, 1)))
                    else:
                        self.window.vm.event.pdirty = True
                case [
                    ["COMPRESSOR"],
                    ["SLIDER", param],
                    ["KEY", "SHIFT", "LEFT" | "RIGHT" | "UP" | "DOWN" as input_direction, "PRESS" | "RELEASE" as e],
                ]:
                    if e == "PRESS":
                        self.window.vm.event.pdirty = False
                        val = getattr(self.window.vm.strip[index].comp, param.lower())

                        match input_direction:
                            case "RIGHT" | "UP":
                                if param == "KNEE":
                                    val += 0.01
                                else:
                                    val += 0.1
                            case "LEFT" | "DOWN":
                                if param == "KNEE":
                                    val -= 0.01
                                else:
                                    val -= 0.1

                        val = CompSlider.check_bounds(param, val)

                        setattr(self.window.vm.strip[index].comp, param.lower(), val)
                        self.popup[f"COMPRESSOR||SLIDER {param}"].update(value=val)
                        if param == "KNEE":
                            self.window.nvda.speak(str(round(val, 2)))
                        else:
                            self.window.nvda.speak(str(round(val, 1)))
                    else:
                        self.window.vm.event.pdirty = True
                case [
                    ["COMPRESSOR"],
                    ["SLIDER", "RELEASE"],
                    ["KEY", "ALT", "LEFT" | "RIGHT" as input_direction, "PRESS" | "RELEASE" as e],
                ]:
                    if e == "PRESS":
                        self.window.vm.event.pdirty = False
                        val = self.window.vm.strip[index].comp.release

                        match input_direction:
                            case "RIGHT" | "UP":
                                val += 10
                            case "LEFT" | "DOWN":
                                val -= 10

                        val = util.check_bounds(val, (0, 5000))
                        self.window.vm.strip[index].comp.release = val
                        self.popup[f"COMPRESSOR||SLIDER {param}"].update(value=val)
                        self.window.nvda.speak(str(round(val, 1)))
                    else:
                        self.window.vm.event.pdirty = True
                case [
                    ["COMPRESSOR"],
                    ["SLIDER", "RELEASE"],
                    ["KEY", "CTRL", "ALT", "LEFT" | "RIGHT" as input_direction, "PRESS" | "RELEASE" as e],
                ]:
                    if e == "PRESS":
                        self.window.vm.event.pdirty = False
                        val = self.window.vm.strip[index].comp.release

                        match input_direction:
                            case "RIGHT" | "UP":
                                val += 50
                            case "LEFT" | "DOWN":
                                val -= 50

                        val = util.check_bounds(val, (0, 5000))
                        self.window.vm.strip[index].comp.release = val
                        self.popup[f"COMPRESSOR||SLIDER {param}"].update(value=val)
                        self.window.nvda.speak(str(round(val, 1)))
                    else:
                        self.window.vm.event.pdirty = True

                case [["COMPRESSOR"], ["SLIDER", "INPUT" | "OUTPUT" as direction, "GAIN"]]:
                    if direction == "INPUT":
                        self.window.vm.strip[index].comp.gainin = values[event]
                    else:
                        self.window.vm.strip[index].comp.gainout = values[event]
                case [["COMPRESSOR"], ["SLIDER", "INPUT" | "OUTPUT" as direction, "GAIN"], ["FOCUS", "IN"]]:
                    label = f"{direction} GAIN"
                    self.window.nvda.speak(f"{label} {values[f'COMPRESSOR||SLIDER {label}']}")
                case [
                    ["COMPRESSOR"],
                    ["SLIDER", "INPUT" | "OUTPUT" as direction, "GAIN"],
                    ["KEY", "LEFT" | "RIGHT" | "UP" | "DOWN" as input_direction, "PRESS" | "RELEASE" as e],
                ]:
                    if e == "PRESS":
                        self.window.vm.event.pdirty = False
                        if direction == "INPUT":
                            val = self.window.vm.strip[index].comp.gainin
                        else:
                            val = self.window.vm.strip[index].comp.gainout

                        match input_direction:
                            case "RIGHT" | "UP":
                                val += 1
                            case "LEFT" | "DOWN":
                                val -= 1

                        val = util.check_bounds(val, (-24, 24))
                        if direction == "INPUT":
                            self.window.vm.strip[index].comp.gainin = val
                        else:
                            self.window.vm.strip[index].comp.gainout = val
                        self.popup[f"COMPRESSOR||SLIDER {direction} GAIN"].update(value=val)
                        self.window.nvda.speak(str(round(val, 1)))
                    else:
                        self.window.vm.event.pdirty = True
                case [
                    ["COMPRESSOR"],
                    ["SLIDER", "INPUT" | "OUTPUT" as direction, "GAIN"],
                    ["KEY", "CTRL", "LEFT" | "RIGHT" | "UP" | "DOWN" as input_direction, "PRESS" | "RELEASE" as e],
                ]:
                    if e == "PRESS":
                        self.window.vm.event.pdirty = False
                        if direction == "INPUT":
                            val = self.window.vm.strip[index].comp.gainin
                        else:
                            val = self.window.vm.strip[index].comp.gainout

                        match input_direction:
                            case "RIGHT" | "UP":
                                val += 3
                            case "LEFT" | "DOWN":
                                val -= 3

                        val = util.check_bounds(val, (-24, 24))
                        if direction == "INPUT":
                            self.window.vm.strip[index].comp.gainin = val
                        else:
                            self.window.vm.strip[index].comp.gainout = val
                        self.popup[f"COMPRESSOR||SLIDER {direction} GAIN"].update(value=val)
                        self.window.nvda.speak(str(round(val, 1)))
                    else:
                        self.window.vm.event.pdirty = True
                case [
                    ["COMPRESSOR"],
                    ["SLIDER", "INPUT" | "OUTPUT" as direction, "GAIN"],
                    ["KEY", "SHIFT", "LEFT" | "RIGHT" | "UP" | "DOWN" as input_direction, "PRESS" | "RELEASE" as e],
                ]:
                    if e == "PRESS":
                        self.window.vm.event.pdirty = False
                        if direction == "INPUT":
                            val = self.window.vm.strip[index].comp.gainin
                        else:
                            val = self.window.vm.strip[index].comp.gainout

                        match input_direction:
                            case "RIGHT" | "UP":
                                val += 0.1
                            case "LEFT" | "DOWN":
                                val -= 0.1

                        val = util.check_bounds(val, (-24, 24))
                        if direction == "INPUT":
                            self.window.vm.strip[index].comp.gainin = val
                        else:
                            self.window.vm.strip[index].comp.gainout = val
                        self.popup[f"COMPRESSOR||SLIDER {direction} GAIN"].update(value=val)
                        self.window.nvda.speak(str(round(val, 1)))
                    else:
                        self.window.vm.event.pdirty = True

                case [
                    ["COMPRESSOR"],
                    ["SLIDER", "INPUT" | "OUTPUT" as direction, "GAIN"],
                    ["KEY", "CTRL", "SHIFT", "R"],
                ]:
                    if direction == "INPUT":
                        self.window.vm.strip[index].comp.gainin = 0
                    else:
                        self.window.vm.strip[index].comp.gainout = 0
                    self.popup[f"COMPRESSOR||SLIDER {direction} GAIN"].update(value=0)
                    self.window.nvda.speak(str(0))
                case [["COMPRESSOR"], ["SLIDER", param], ["KEY", "CTRL", "SHIFT", "R"]]:
                    match param:
                        case "RATIO":
                            val = 1
                        case "THRESHOLD":
                            val = -20
                        case "ATTACK":
                            val = 10
                        case "RELEASE":
                            val = 50
                        case "KNEE":
                            val = 0.5
                    setattr(self.window.vm.strip[index].comp, param.lower(), val)
                    self.popup[f"COMPRESSOR||SLIDER {param}"].update(value=val)
                    self.window.nvda.speak(str(round(val, 1)))

                case ["MAKEUP"]:
                    val = not self.window.vm.strip[index].comp.makeup
                    self.window.vm.strip[index].comp.makeup = val
                    self.window.nvda.speak("on" if val else "off")
                case [[button], ["FOCUS", "IN"]]:
                    if button == "MAKEUP":
                        self.window.nvda.speak(
                            f"{button} {'on' if self.window.vm.strip[index].comp.makeup else 'off'}"
                        )
                    else:
                        self.window.nvda.speak(button)
                case [_, ["KEY", "ENTER"]]:
                    self.popup.find_element_with_focus().click()
            self.logger.debug(f"parsed::{parsed_cmd}")
        self.window.vm.observer.remove(self.on_pdirty)
        self.popup.close()

    def gate(self, index, title=None):
        self.index = index

        def _make_gate_frame() -> psg.Frame:
            gate_layout = [
                [LabelSliderAdvanced(self.window, index, param, GateSlider)]
                for param in ("THRESHOLD", "DAMPING", "BPSIDECHAIN", "ATTACK", "HOLD", "RELEASE")
            ]
            return psg.Frame("ADVANCED GATE", gate_layout)

        layout = []
        steps = (_make_gate_frame,)
        for step in steps:
            layout.append([step()])
        layout.append([psg.Button("Exit", size=(8, 1))])

        self.popup = psg.Window(title, layout, return_keyboard_events=False, finalize=True)
        buttonmenu_opts = {"takefocus": 1, "highlightthickness": 1}
        for param in ("THRESHOLD", "DAMPING", "BPSIDECHAIN", "ATTACK", "HOLD", "RELEASE"):
            self.popup[f"GATE||SLIDER {param}"].Widget.config(**buttonmenu_opts)
            self.popup[f"GATE||SLIDER {param}"].bind("<FocusIn>", "||FOCUS IN")
            self.popup[f"GATE||SLIDER {param}"].bind("<FocusOut>", "||FOCUS OUT")
            for event in ("KeyPress", "KeyRelease"):
                event_id = event.removeprefix("Key").upper()
                for direction in ("Left", "Right", "Up", "Down"):
                    self.popup[f"GATE||SLIDER {param}"].bind(
                        f"<{event}-{direction}>", f"||KEY {direction.upper()} {event_id}"
                    )
                    self.popup[f"GATE||SLIDER {param}"].bind(
                        f"<Shift-{event}-{direction}>", f"||KEY SHIFT {direction.upper()} {event_id}"
                    )
                    self.popup[f"GATE||SLIDER {param}"].bind(
                        f"<Control-{event}-{direction}>", f"||KEY CTRL {direction.upper()} {event_id}"
                    )
                    if param in ("BPSIDECHAIN", "ATTACK", "HOLD", "RELEASE"):
                        self.popup[f"GATE||SLIDER {param}"].bind(
                            f"<Alt-{event}-{direction}>", f"||KEY ALT {direction.upper()} {event_id}"
                        )
                        self.popup[f"GATE||SLIDER {param}"].bind(
                            f"<Control-Alt-{event}-{direction}>", f"||KEY CTRL ALT {direction.upper()} {event_id}"
                        )
            self.popup[f"GATE||SLIDER {param}"].bind("<Control-Shift-KeyPress-R>", "||KEY CTRL SHIFT R")
        self.popup["Exit"].bind("<FocusIn>", "||FOCUS IN")
        self.popup["Exit"].bind("<Return>", "||KEY ENTER")
        self.window.vm.observer.add(self.on_pdirty)
        while True:
            event, values = self.popup.read()
            self.logger.debug(f"event::{event}")
            self.logger.debug(f"values::{values}")
            if event in (psg.WIN_CLOSED, "Exit"):
                break
            match parsed_cmd := self.window.parser.match.parseString(event):
                case [["GATE"], ["SLIDER", param]]:
                    setattr(self.window.vm.strip[index].gate, param.lower(), values[event])
                case [["GATE"], ["SLIDER", param], ["FOCUS", "IN"]]:
                    label_map = {
                        "DAMPING": "Damping Max",
                        "BPSIDECHAIN": "BP Sidechain",
                    }
                    self.window.nvda.speak(f"{label_map.get(param, param)} {values[f'GATE||SLIDER {param}']}")

                case [
                    ["GATE"],
                    ["SLIDER", param],
                    ["KEY", "LEFT" | "RIGHT" | "UP" | "DOWN" as input_direction, "PRESS" | "RELEASE" as e],
                ]:
                    if e == "PRESS":
                        self.window.vm.event.pdirty = False
                        val = getattr(self.window.vm.strip[index].gate, param.lower())

                        match input_direction:
                            case "RIGHT" | "UP":
                                val += 1
                            case "LEFT" | "DOWN":
                                val -= 1

                        val = GateSlider.check_bounds(param, val)

                        setattr(self.window.vm.strip[index].gate, param.lower(), val)
                        self.popup[f"GATE||SLIDER {param}"].update(value=val)
                        if param == "BPSIDECHAIN":
                            self.window.nvda.speak(str(int(val)))
                        else:
                            self.window.nvda.speak(str(round(val, 1)))
                    else:
                        self.window.vm.event.pdirty = True
                case [
                    ["GATE"],
                    ["SLIDER", param],
                    ["KEY", "CTRL", "LEFT" | "RIGHT" | "UP" | "DOWN" as input_direction, "PRESS" | "RELEASE" as e],
                ]:
                    if e == "PRESS":
                        self.window.vm.event.pdirty = False
                        val = getattr(self.window.vm.strip[index].gate, param.lower())

                        match input_direction:
                            case "RIGHT" | "UP":
                                val += 3
                            case "LEFT" | "DOWN":
                                val -= 3

                        val = GateSlider.check_bounds(param, val)

                        setattr(self.window.vm.strip[index].gate, param.lower(), val)
                        self.popup[f"GATE||SLIDER {param}"].update(value=val)
                        if param == "BPSIDECHAIN":
                            self.window.nvda.speak(str(int(val)))
                        else:
                            self.window.nvda.speak(str(round(val, 1)))
                    else:
                        self.window.vm.event.pdirty = True
                case [
                    ["GATE"],
                    ["SLIDER", param],
                    ["KEY", "SHIFT", "LEFT" | "RIGHT" | "UP" | "DOWN" as input_direction, "PRESS" | "RELEASE" as e],
                ]:
                    if e == "PRESS":
                        self.window.vm.event.pdirty = False
                        val = getattr(self.window.vm.strip[index].gate, param.lower())

                        match input_direction:
                            case "RIGHT" | "UP":
                                val += 0.1
                            case "LEFT" | "DOWN":
                                val -= 0.1

                        val = GateSlider.check_bounds(param, val)

                        setattr(self.window.vm.strip[index].gate, param.lower(), val)
                        self.popup[f"GATE||SLIDER {param}"].update(value=val)
                        if param == "BPSIDECHAIN":
                            self.window.nvda.speak(str(int(val)))
                        else:
                            self.window.nvda.speak(str(round(val, 1)))
                    else:
                        self.window.vm.event.pdirty = True
                case [
                    ["GATE"],
                    ["SLIDER", "BPSIDECHAIN" | "ATTACK" | "HOLD" | "RELEASE" as param],
                    ["KEY", "ALT", "LEFT" | "RIGHT" as input_direction, "PRESS" | "RELEASE" as e],
                ]:
                    if e == "PRESS":
                        self.window.vm.event.pdirty = False
                        val = getattr(self.window.vm.strip[index].gate, param.lower())

                        match input_direction:
                            case "RIGHT" | "UP":
                                val += 10
                            case "LEFT" | "DOWN":
                                val -= 10

                        val = GateSlider.check_bounds(param, val)
                        setattr(self.window.vm.strip[index].gate, param.lower(), val)
                        self.popup[f"GATE||SLIDER {param}"].update(value=val)
                        if param == "BPSIDECHAIN":
                            self.window.nvda.speak(str(int(val)))
                        else:
                            self.window.nvda.speak(str(round(val, 1)))
                    else:
                        self.window.vm.event.pdirty = True
                case [
                    ["GATE"],
                    ["SLIDER", "BPSIDECHAIN" | "ATTACK" | "HOLD" | "RELEASE" as param],
                    ["KEY", "CTRL", "ALT", "LEFT" | "RIGHT" as input_direction, "PRESS" | "RELEASE" as e],
                ]:
                    if e == "PRESS":
                        self.window.vm.event.pdirty = False
                        val = getattr(self.window.vm.strip[index].gate, param.lower())

                        match input_direction:
                            case "RIGHT" | "UP":
                                val += 50
                            case "LEFT" | "DOWN":
                                val -= 50

                        val = GateSlider.check_bounds(param, val)
                        setattr(self.window.vm.strip[index].gate, param.lower(), val)
                        self.popup[f"GATE||SLIDER {param}"].update(value=val)
                        if param == "BPSIDECHAIN":
                            self.window.nvda.speak(str(int(val)))
                        else:
                            self.window.nvda.speak(str(round(val, 1)))
                    else:
                        self.window.vm.event.pdirty = True
                case [["GATE"], ["SLIDER", param], ["KEY", "CTRL", "SHIFT", "R"]]:
                    match param:
                        case "THRESHOLD":
                            val = -60
                        case "DAMPING":
                            val = -60
                        case "BPSIDECHAIN":
                            val = 100
                        case "ATTACK":
                            val = 0
                        case "HOLD":
                            val = 500
                        case "RELEASE":
                            val = 1000
                    setattr(self.window.vm.strip[index].gate, param.lower(), val)
                    self.popup[f"GATE||SLIDER {param}"].update(value=val)
                    self.window.nvda.speak(str(round(val, 1)))

                case [[button], ["FOCUS", "IN"]]:
                    self.window.nvda.speak(button)
                case [_, ["KEY", "ENTER"]]:
                    self.popup.find_element_with_focus().click()

            self.logger.debug(f"parsed::{parsed_cmd}")
        self.window.vm.observer.remove(self.on_pdirty)
        self.popup.close()
