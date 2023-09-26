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

        popup = psg.Window(title, layout, finalize=True)
        buttonmenu_opts = {"takefocus": 1, "highlightthickness": 1}
        for driver in ("MME", "WDM", "KS", "ASIO"):
            popup[f"BUFFER {driver}"].Widget.config(**buttonmenu_opts)
            popup[f"BUFFER {driver}"].bind("<FocusIn>", "||FOCUS IN")
            popup[f"BUFFER {driver}"].bind("<space>", "||KEY SPACE", propagate=False)
            popup[f"BUFFER {driver}"].bind("<Return>", "||KEY ENTER", propagate=False)
        popup["Exit"].bind("<FocusIn>", "||FOCUS IN")
        popup["Exit"].bind("<Return>", "||KEY ENTER")
        while True:
            event, values = popup.read()
            self.logger.debug(f"event::{event}")
            self.logger.debug(f"values::{values}")
            if event in (psg.WIN_CLOSED, "Exit"):
                break
            match parsed_cmd := self.window.parser.match.parseString(event):
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
                    util.open_context_menu_for_buttonmenu(popup, f"BUFFER {driver}")
                case [[button], ["FOCUS", "IN"]]:
                    self.window.nvda.speak(button)
                case [_, ["KEY", "ENTER"]]:
                    popup.find_element_with_focus().click()
            self.logger.debug(f"parsed::{parsed_cmd}")
        popup.close()

    def compressor(self, index, title=None):
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

        popup = psg.Window(title, layout, return_keyboard_events=False, finalize=True)
        buttonmenu_opts = {"takefocus": 1, "highlightthickness": 1}
        for param in ("INPUT GAIN", "RATIO", "THRESHOLD", "ATTACK", "RELEASE", "KNEE", "OUTPUT GAIN"):
            popup[f"COMPRESSOR||SLIDER {param}"].Widget.config(**buttonmenu_opts)
            popup[f"COMPRESSOR||SLIDER {param}"].bind("<FocusIn>", "||FOCUS IN")
            popup[f"COMPRESSOR||SLIDER {param}"].bind("<FocusOut>", "||FOCUS OUT")
            for event in ("KeyPress", "KeyRelease"):
                event_id = event.removeprefix("Key").upper()
                for direction in ("Left", "Right", "Up", "Down"):
                    popup[f"COMPRESSOR||SLIDER {param}"].bind(
                        f"<{event}-{direction}>", f"||KEY {direction.upper()} {event_id}"
                    )
                    popup[f"COMPRESSOR||SLIDER {param}"].bind(
                        f"<Shift-{event}-{direction}>", f"||KEY SHIFT {direction.upper()} {event_id}"
                    )
                    popup[f"COMPRESSOR||SLIDER {param}"].bind(
                        f"<Control-{event}-{direction}>", f"||KEY CTRL {direction.upper()} {event_id}"
                    )
                    if param == "RELEASE":
                        popup[f"COMPRESSOR||SLIDER {param}"].bind(
                            f"<Alt-{event}-{direction}>", f"||KEY ALT {direction.upper()} {event_id}"
                        )
                        popup[f"COMPRESSOR||SLIDER {param}"].bind(
                            f"<Control-Alt-{event}-{direction}>", f"||KEY CTRL ALT {direction.upper()} {event_id}"
                        )
        popup["MAKEUP"].bind("<FocusIn>", "||FOCUS IN")
        popup["MAKEUP"].bind("<Return>", "||KEY ENTER")
        popup["Exit"].bind("<FocusIn>", "||FOCUS IN")
        popup["Exit"].bind("<Return>", "||KEY ENTER")
        while True:
            event, values = popup.read()
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
                        popup[f"COMPRESSOR||SLIDER {param}"].update(value=val)
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
                        popup[f"COMPRESSOR||SLIDER {param}"].update(value=val)
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
                        popup[f"COMPRESSOR||SLIDER {param}"].update(value=val)
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
                        popup[f"COMPRESSOR||SLIDER {param}"].update(value=val)
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
                        popup[f"COMPRESSOR||SLIDER {param}"].update(value=val)
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
                        popup[f"COMPRESSOR||SLIDER {direction} GAIN"].update(value=val)
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
                        popup[f"COMPRESSOR||SLIDER {direction} GAIN"].update(value=val)
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
                        popup[f"COMPRESSOR||SLIDER {direction} GAIN"].update(value=val)
                        self.window.nvda.speak(str(round(val, 1)))
                    else:
                        self.window.vm.event.pdirty = True

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
                    popup.find_element_with_focus().click()
            self.logger.debug(f"parsed::{parsed_cmd}")
        popup.close()

    def gate(self, index, title=None):
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

        popup = psg.Window(title, layout, return_keyboard_events=False, finalize=True)
        buttonmenu_opts = {"takefocus": 1, "highlightthickness": 1}
        for param in ("THRESHOLD", "DAMPING", "BPSIDECHAIN", "ATTACK", "HOLD", "RELEASE"):
            popup[f"GATE||SLIDER {param}"].Widget.config(**buttonmenu_opts)
            popup[f"GATE||SLIDER {param}"].bind("<FocusIn>", "||FOCUS IN")
            popup[f"GATE||SLIDER {param}"].bind("<FocusOut>", "||FOCUS OUT")
            for event in ("KeyPress", "KeyRelease"):
                event_id = event.removeprefix("Key").upper()
                for direction in ("Left", "Right", "Up", "Down"):
                    popup[f"GATE||SLIDER {param}"].bind(
                        f"<{event}-{direction}>", f"||KEY {direction.upper()} {event_id}"
                    )
                    popup[f"GATE||SLIDER {param}"].bind(
                        f"<Shift-{event}-{direction}>", f"||KEY SHIFT {direction.upper()} {event_id}"
                    )
                    popup[f"GATE||SLIDER {param}"].bind(
                        f"<Control-{event}-{direction}>", f"||KEY CTRL {direction.upper()} {event_id}"
                    )
                    if param in ("BPSIDECHAIN", "ATTACK", "HOLD", "RELEASE"):
                        popup[f"GATE||SLIDER {param}"].bind(
                            f"<Alt-{event}-{direction}>", f"||KEY ALT {direction.upper()} {event_id}"
                        )
                        popup[f"GATE||SLIDER {param}"].bind(
                            f"<Control-Alt-{event}-{direction}>", f"||KEY CTRL ALT {direction.upper()} {event_id}"
                        )
        popup["Exit"].bind("<FocusIn>", "||FOCUS IN")
        popup["Exit"].bind("<Return>", "||KEY ENTER")
        while True:
            event, values = popup.read()
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
                        popup[f"GATE||SLIDER {param}"].update(value=val)
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
                        popup[f"GATE||SLIDER {param}"].update(value=val)
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
                        popup[f"GATE||SLIDER {param}"].update(value=val)
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
                        popup[f"GATE||SLIDER {param}"].update(value=val)
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
                        popup[f"GATE||SLIDER {param}"].update(value=val)
                        if param == "BPSIDECHAIN":
                            self.window.nvda.speak(str(int(val)))
                        else:
                            self.window.nvda.speak(str(round(val, 1)))
                    else:
                        self.window.vm.event.pdirty = True

                case [[button], ["FOCUS", "IN"]]:
                    self.window.nvda.speak(button)
                case [_, ["KEY", "ENTER"]]:
                    popup.find_element_with_focus().click()

            self.logger.debug(f"parsed::{parsed_cmd}")
        popup.close()
