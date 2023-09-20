import logging
from pathlib import Path

import PySimpleGUI as psg

from . import util

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
                case [[button], ["KEY", "ENTER"]]:
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
                case [[button], ["KEY", "ENTER"]]:
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
                case [[button], ["KEY", "ENTER"]]:
                    popup.find_element_with_focus().click()
            self.logger.debug(f"parsed::{parsed_cmd}")
        popup.close()
