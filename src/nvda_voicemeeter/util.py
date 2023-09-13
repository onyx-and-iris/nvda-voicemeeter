def get_asio_checkbox_index(channel, num) -> int:
    if channel == 0:
        return 2 * num - 2
    return 2 * num - 1


def get_insert_checkbox_index(kind, channel, num) -> int:
    if num <= kind.phys_in:
        if channel == 0:
            return 2 * num - 2
        else:
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
        [temp.append(f"IN#{i + 1} {channel}") for channel in ("Left", "Right", "Center", "LFE", "SL", "SR", "BL", "BR")]
    temp.append(f"BUS Channel")
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


def get_asio_samples_list() -> list:
    return [
        "1024",
        "768",
        "704",
        "640",
        "576",
        "512",
        "480",
        "448",
        "441",
        "416",
        "384",
        "352",
        "320",
        "288",
        "256",
        "224",
        "192",
        "160",
        "128",
    ]


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
