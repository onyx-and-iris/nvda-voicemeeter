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
