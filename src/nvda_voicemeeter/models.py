def _make_hardware_ins_cache(vm) -> dict:
    return {**{f"HARDWARE IN||{i + 1}": vm.strip[i].device.name for i in range(vm.kind.phys_in)}}


def _make_hardware_outs_cache(vm) -> dict:
    hw_outs = {**{f"HARDWARE OUT||A{i + 1}": vm.bus[i].device.name for i in range(vm.kind.phys_out)}}
    if vm.kind.name == "basic":
        hw_outs |= {"HARDWARE OUT||A2": vm.bus[1].device.name}
    return hw_outs


def _make_param_cache(vm, channel_type) -> dict:
    params = {}
    if channel_type == "strip":
        match vm.kind.name:
            case "basic":
                params |= {
                    **{f"STRIP {i}||A1": vm.strip[i].A1 for i in range(vm.kind.num_strip)},
                    **{f"STRIP {i}||B1": vm.strip[i].B1 for i in range(vm.kind.num_strip)},
                }
            case "banana":
                params |= {
                    **{f"STRIP {i}||A1": vm.strip[i].A1 for i in range(vm.kind.num_strip)},
                    **{f"STRIP {i}||A2": vm.strip[i].A2 for i in range(vm.kind.num_strip)},
                    **{f"STRIP {i}||A3": vm.strip[i].A3 for i in range(vm.kind.num_strip)},
                    **{f"STRIP {i}||B1": vm.strip[i].B1 for i in range(vm.kind.num_strip)},
                    **{f"STRIP {i}||B2": vm.strip[i].B2 for i in range(vm.kind.num_strip)},
                }
            case "potato":
                params |= {
                    **{f"STRIP {i}||A1": vm.strip[i].A1 for i in range(vm.kind.num_strip)},
                    **{f"STRIP {i}||A2": vm.strip[i].A2 for i in range(vm.kind.num_strip)},
                    **{f"STRIP {i}||A3": vm.strip[i].A3 for i in range(vm.kind.num_strip)},
                    **{f"STRIP {i}||A4": vm.strip[i].A4 for i in range(vm.kind.num_strip)},
                    **{f"STRIP {i}||A5": vm.strip[i].A5 for i in range(vm.kind.num_strip)},
                    **{f"STRIP {i}||B1": vm.strip[i].B1 for i in range(vm.kind.num_strip)},
                    **{f"STRIP {i}||B2": vm.strip[i].B2 for i in range(vm.kind.num_strip)},
                    **{f"STRIP {i}||B3": vm.strip[i].B3 for i in range(vm.kind.num_strip)},
                }
        params |= {
            **{f"STRIP {i}||MONO": vm.strip[i].mono for i in range(vm.kind.num_strip)},
            **{f"STRIP {i}||SOLO": vm.strip[i].solo for i in range(vm.kind.num_strip)},
            **{f"STRIP {i}||MUTE": vm.strip[i].mute for i in range(vm.kind.num_strip)},
        }
    else:
        params |= {
            **{f"BUS {i}||MONO": vm.bus[i].mono for i in range(vm.kind.num_bus)},
            **{f"BUS {i}||EQ": vm.bus[i].eq.on for i in range(vm.kind.num_bus)},
            **{f"BUS {i}||MUTE": vm.bus[i].mute for i in range(vm.kind.num_bus)},
            **{f"BUS {i}||MODE": vm.bus[i].mode.get() for i in range(vm.kind.num_bus)},
        }
    return params


def _make_label_cache(vm) -> dict:
    return {
        **{
            f"STRIP {i}||LABEL": vm.strip[i].label if vm.strip[i].label else f"Hardware Input {i + 1}"
            for i in range(vm.kind.phys_in)
        },
        **{
            f"STRIP {i}||LABEL": vm.strip[i].label if vm.strip[i].label else f"Virtual Input {i - vm.kind.phys_in + 1}"
            for i in range(vm.kind.phys_in, vm.kind.phys_in + vm.kind.virt_in)
        },
        **{
            f"BUS {i}||LABEL": vm.bus[i].label if vm.bus[i].label else f"Physical Bus {i + 1}"
            for i in range(vm.kind.phys_out)
        },
        **{
            f"BUS {i}||LABEL": vm.bus[i].label if vm.bus[i].label else f"Virtual Bus {i - vm.kind.phys_out + 1}"
            for i in range(vm.kind.phys_out, vm.kind.phys_out + vm.kind.virt_out)
        },
    }


def _make_patch_asio_cache(vm) -> dict:
    if vm.kind.name != "basic":
        return {**{f"ASIO CHECKBOX||{i}": vm.patch.asio[i].get() for i in range(vm.kind.phys_out * 2)}}


def _make_patch_insert_cache(vm) -> dict:
    if vm.kind.name != "basic":
        return {**{f"INSERT CHECKBOX||{i}": vm.patch.insert[i].on for i in range(vm.kind.num_strip_levels)}}
