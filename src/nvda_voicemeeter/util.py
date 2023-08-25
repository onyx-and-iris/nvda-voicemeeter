def get_asio_checkbox_index(channel, num):
    if channel == 0:
        return 2 * num - 2
    return 2 * num - 1


def get_insert_checkbox_index(kind, channel, num):
    if num <= kind.phys_in:
        if channel == 0:
            return 2 * num - 2
        else:
            return 2 * num - 1
    return (2 * kind.phys_in) + (8 * (num - kind.phys_in - 1)) + channel


def get_input_device_list(vm):
    return ["{type}: {name}".format(**vm.device.output(i)) for i in range(vm.device.outs)]


def get_patch_composite_list(kind):
    temp = []
    for i in range(kind.phys_out):
        [temp.append(f"IN#{i + 1} {channel}") for channel in ("Left", "Right")]
    for i in range(kind.phys_out, kind.phys_out + kind.virt_out):
        [temp.append(f"IN#{i + 1} {channel}") for channel in ("Left", "Right", "Center", "LFE", "SL", "SR", "BL", "BR")]
    temp.append(f"BUS Channel")
    return temp
