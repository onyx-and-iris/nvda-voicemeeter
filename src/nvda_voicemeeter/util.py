from typing import Iterable

import PySimpleGUI as psg


def get_asio_input_spinbox_index(channel, num) -> int:
    if channel == 0:
        return 2 * num - 2
    return 2 * num - 1


def get_insert_checkbox_index(kind, channel, num) -> int:
    if num <= kind.phys_in:
        if channel == 0:
            return 2 * num - 2
        return 2 * num - 1
    return (2 * kind.phys_in) + (8 * (num - kind.phys_in - 1)) + channel


_rejected_ids = (
    "VBAudio100VMVAIO3",
    "{F5735BD4-6EAF-4758-9710-9886E5AD0FF3}",
    "{0239BE07-CEEF-4236-A900-AA778D432FD4}",
)


def get_input_device_list(vm) -> list:
    devices = []
    for j in range(vm.device.ins):
        device = vm.device.input(j)
        if device["id"] not in _rejected_ids:
            devices.append("{type}: {name}".format(**device))
    return devices


def get_output_device_list(i, vm) -> list:
    devices = []
    for j in range(vm.device.outs):
        device = vm.device.output(j)
        if device["id"] not in _rejected_ids:
            devices.append("{type}: {name}".format(**device))
    if i == 0:
        return devices
    devices.append("- remove device selection -")
    return [device for device in devices if not device.startswith("asio")]


def get_patch_composite_list(kind) -> list:
    temp = []
    for i in range(kind.phys_out):
        [temp.append(f"IN#{i + 1} {channel}") for channel in ("Left", "Right")]
    for i in range(kind.phys_out, kind.phys_out + kind.virt_out):
        [
            temp.append(f"IN#{i + 1} {channel}")
            for channel in ("Left", "Right", "Center", "LFE", "SL", "SR", "BL", "BR")
        ]
    temp.append("BUS Channel")
    return temp


def get_patch_insert_channels() -> list:
    return [
        "left",
        "right",
        "center",
        "low frequency effect",
        "surround left",
        "surround right",
        "back left",
        "back right",
    ]


_patch_insert_channels = get_patch_insert_channels()


def get_asio_samples_list(driver) -> list:
    if driver == "MME":
        samples = ["2048", "1536", "1024", "896", "768", "704", "640", "576", "512", "480", "441"]
    else:
        # fmt: off
        samples = [
            "2048", "1536", "1024", "768", "704", "640", "576", "512", "480", "448", "441", "416", "384",
            "352", "320", "288", "256", "224", "192", "160", "128"
        ]
        # fmt: on
        if driver == "ASIO":
            samples = [x for x in samples if x not in ("2048", "1536")]
    samples.append("Default")
    return samples


def get_tabs_labels() -> list:
    return ["Settings", "Physical Strip", "Virtual Strip", "Buses"]


def open_context_menu_for_buttonmenu(window, identifier) -> None:
    element = window[identifier]
    widget = element.widget
    x = widget.winfo_rootx()
    y = widget.winfo_rooty() + widget.winfo_height()
    element.TKMenu.post(x, y)


def get_channel_identifier_list(vm) -> list:
    identifiers = []
    for i in range(vm.kind.phys_in):
        for j in range(2):
            identifiers.append(f"IN{i + 1} {j}")
    for i in range(vm.kind.phys_in, vm.kind.phys_in + vm.kind.virt_in):
        for j in range(8):
            identifiers.append(f"IN{i + 1} {j}")
    return identifiers


_bus_mode_map = {
    "normal": "Normal",
    "amix": "Mix Down A",
    "bmix": "Mix Down B",
    "repeat": "Stereo Repeat",
    "composite": "Composite",
    "tvmix": "Up Mix TV",
    "upmix21": "Up Mix 2.1",
    "upmix41": "Up Mix 4.1",
    "upmix61": "Up Mix 6.1",
    "centeronly": "Center Only",
    "lfeonly": "Low Frequency Effect Only",
    "rearonly": "Rear Only",
}

_bus_mode_map_reversed = dict((reversed(item) for item in _bus_mode_map.items()))


def get_bus_modes(vm) -> list:
    if vm.kind.name == "basic":
        return [
            "normal",
            "amix",
            "repeat",
            "composite",
        ]
    return [
        "normal",
        "amix",
        "bmix",
        "repeat",
        "composite",
        "tvmix",
        "upmix21",
        "upmix41",
        "upmix61",
        "centeronly",
        "lfeonly",
        "rearonly",
    ]


def check_bounds(val, bounds: tuple) -> int | float:
    lower, upper = bounds
    if val > upper:
        val = upper
    elif val < lower:
        val = lower
    return val


def get_slider_params(i, kind) -> Iterable:
    if i < kind.phys_in:
        if kind.name == "basic":
            return ("AUDIBILITY",)
        if kind.name == "banana":
            return ("COMP", "GATE")
        if kind.name == "potato":
            return ("COMP", "GATE", "DENOISER")
    return ("BASS", "MID", "TREBLE")


def get_full_slider_params(i, kind) -> Iterable:
    params = list(get_slider_params(i, kind) + ("GAIN", "LIMIT"))
    if kind.name == "basic":
        params.remove("LIMIT")
    return params


def get_slider_modes() -> Iterable:
    return (
        "GAIN MODE",
        "BASS MODE",
        "MID MODE",
        "TREBLE MODE",
        "AUDIBILITY MODE",
        "COMP MODE",
        "GATE MODE",
        "DENOISER MODE",
        "LIMIT MODE",
    )


def _get_bus_assignments(kind) -> list:
    return [f"A{i}" for i in range(1, kind.phys_out + 1)] + [f"B{i}" for i in range(1, kind.virt_out + 1)]


psg.theme_add_new(
    "HighContrast",
    {
        "BACKGROUND": "#FFFFFF",
        "TEXT": "#000000",
        "INPUT": "#FAF9F6",
        "TEXT_INPUT": "#000000",
        "SCROLL": "#FAF9F6",
        "BUTTON": ("#000000", "#FFFFFF"),
        "PROGRESS": ("#000000", "#FFFFFF"),
        "BORDER": 2,
        "SLIDER_DEPTH": 3,
        "PROGRESS_DEPTH": 0,
    },
)


def get_themes_list() -> list:
    return [
        "Bright Colors",
        "Dark Blue 14",
        "Dark Brown 2",
        "Dark Brown 3",
        "Dark Green 2",
        "Dark Grey 2",
        "Dark Teal1",
        "Dark Teal6",
        "Kayak",
        "Light Blue 2",
        "Light Brown 2",
        "Light Brown 5",
        "Light Green",
        "Light Green 3",
        "Light Grey 2",
        "Light Purple",
        "Neutral Blue",
        "Reds",
        "Sandy Beach",
        "High Contrast",
    ]
