def _make_cache(vm) -> dict:
    match vm.kind.name:
        case "basic":
            return {
                **{f"BUTTON||strip {i} A1": vm.strip[i].A1 for i in range(vm.kind.num_strip)},
                **{f"BUTTON||strip {i} B1": vm.strip[i].B1 for i in range(vm.kind.num_strip)},
            }
        case "banana":
            return {
                **{f"BUTTON||strip {i} A1": vm.strip[i].A1 for i in range(vm.kind.num_strip)},
                **{f"BUTTON||strip {i} A2": vm.strip[i].A2 for i in range(vm.kind.num_strip)},
                **{f"BUTTON||strip {i} A3": vm.strip[i].A3 for i in range(vm.kind.num_strip)},
                **{f"BUTTON||strip {i} B1": vm.strip[i].B1 for i in range(vm.kind.num_strip)},
                **{f"BUTTON||strip {i} B2": vm.strip[i].B2 for i in range(vm.kind.num_strip)},
            }
        case "potato":
            return {
                **{f"BUTTON||strip {i} A1": vm.strip[i].A1 for i in range(vm.kind.num_strip)},
                **{f"BUTTON||strip {i} A2": vm.strip[i].A2 for i in range(vm.kind.num_strip)},
                **{f"BUTTON||strip {i} A3": vm.strip[i].A3 for i in range(vm.kind.num_strip)},
                **{f"BUTTON||strip {i} A4": vm.strip[i].A4 for i in range(vm.kind.num_strip)},
                **{f"BUTTON||strip {i} A5": vm.strip[i].A5 for i in range(vm.kind.num_strip)},
                **{f"BUTTON||strip {i} B1": vm.strip[i].B1 for i in range(vm.kind.num_strip)},
                **{f"BUTTON||strip {i} B2": vm.strip[i].B2 for i in range(vm.kind.num_strip)},
                **{f"BUTTON||strip {i} B3": vm.strip[i].B3 for i in range(vm.kind.num_strip)},
            }


_patch_insert_channels = (
    "left",
    "right",
    "center",
    "low frequency effect",
    "surround left",
    "surround right",
    "back left",
    "back right",
)
