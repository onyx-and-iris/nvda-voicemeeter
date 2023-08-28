def _make_output_cache(vm) -> dict:
    match vm.kind.name:
        case "basic":
            return {
                **{f"STRIP {i}||A1": vm.strip[i].A1 for i in range(vm.kind.num_strip)},
                **{f"STRIP {i}||B1": vm.strip[i].B1 for i in range(vm.kind.num_strip)},
            }
        case "banana":
            return {
                **{f"STRIP {i}||A1": vm.strip[i].A1 for i in range(vm.kind.num_strip)},
                **{f"STRIP {i}||A2": vm.strip[i].A2 for i in range(vm.kind.num_strip)},
                **{f"STRIP {i}||A3": vm.strip[i].A3 for i in range(vm.kind.num_strip)},
                **{f"STRIP {i}||B1": vm.strip[i].B1 for i in range(vm.kind.num_strip)},
                **{f"STRIP {i}||B2": vm.strip[i].B2 for i in range(vm.kind.num_strip)},
            }
        case "potato":
            return {
                **{f"STRIP {i}||A1": vm.strip[i].A1 for i in range(vm.kind.num_strip)},
                **{f"STRIP {i}||A2": vm.strip[i].A2 for i in range(vm.kind.num_strip)},
                **{f"STRIP {i}||A3": vm.strip[i].A3 for i in range(vm.kind.num_strip)},
                **{f"STRIP {i}||A4": vm.strip[i].A4 for i in range(vm.kind.num_strip)},
                **{f"STRIP {i}||A5": vm.strip[i].A5 for i in range(vm.kind.num_strip)},
                **{f"STRIP {i}||B1": vm.strip[i].B1 for i in range(vm.kind.num_strip)},
                **{f"STRIP {i}||B2": vm.strip[i].B2 for i in range(vm.kind.num_strip)},
                **{f"STRIP {i}||B3": vm.strip[i].B3 for i in range(vm.kind.num_strip)},
            }


def _make_bus_mode_cache(vm) -> dict:
    return {**{f"BUS {i}||MODE": vm.bus[i].mode.get() for i in range(vm.kind.num_bus)}}
