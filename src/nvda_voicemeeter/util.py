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


def get_input_device_list(vm) -> list:
    return ["{type}: {name}".format(**vm.device.output(i)) for i in range(vm.device.outs)]


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
