import PySimpleGUI as psg


class Builder:
    """Responsible for building the Window layout"""

    def __init__(self, window, vm):
        self.window = window
        self.vm = vm
        self.kind = self.vm.kind

    def run(self) -> list:
        row0 = self.make_row0()
        row1 = self.make_row1()
        row2 = self.make_row2()
        return [[row0], [row1], [row2]]

    def make_row0(self):
        def add_physical_device_opts(layout):
            devices = ["{type}: {name}".format(**self.vm.device.output(i)) for i in range(self.vm.device.outs)]
            devices.append("Deselect Device")
            layout.append(
                [
                    psg.Combo(
                        devices,
                        size=(22, 4),
                        expand_x=True,
                        enable_events=True,
                        readonly=True,
                        key=f"HARDWARE OUT||A{i}",
                    )
                    for i in range(1, self.kind.phys_out + 1)
                ]
            )

        hardware_out = list()
        [step(hardware_out) for step in (add_physical_device_opts,)]
        return psg.Frame("Hardware Out", hardware_out)

    def make_row1(self):
        def add_asio_checkboxes(layout, i):
            nums = list(range(99))
            layout.append(
                [psg.Spin(nums, initial_value=0, size=2, enable_events=True, key=f"ASIO CHECKBOX||IN{i} 0")],
            )
            layout.append(
                [psg.Spin(nums, initial_value=0, size=2, enable_events=True, key=f"ASIO CHECKBOX||IN{i} 1")],
            )

        inner = list()
        asio_checkboxlists = ([] for _ in range(self.kind.phys_out))
        for i, checkbox_list in enumerate(asio_checkboxlists):
            [step(checkbox_list, i + 1) for step in (add_asio_checkboxes,)]
            inner.append(psg.Frame(f"In#{i + 1}", checkbox_list))

        asio_checkboxes = [inner]
        return psg.Frame("PATCH ASIO Inputs to Strips", asio_checkboxes)

    def make_row2(self):
        def add_insert_checkboxes(layout, i):
            if i <= self.kind.phys_in:
                layout.append(
                    [psg.Checkbox(text="LEFT", enable_events=True, key=f"INSERT CHECKBOX||IN{i} 0")],
                )
                layout.append(
                    [psg.Checkbox(text="RIGHT", enable_events=True, key=f"INSERT CHECKBOX||IN{i} 1")],
                )
            else:
                layout.append(
                    [
                        psg.Checkbox(text="LEFT", enable_events=True, key=f"INSERT CHECKBOX||IN{i} 0"),
                        psg.Checkbox(text="RIGHT", enable_events=True, key=f"INSERT CHECKBOX||IN{i} 1"),
                        psg.Checkbox(text="C", enable_events=True, key=f"INSERT CHECKBOX||IN{i} 2"),
                        psg.Checkbox(text="LFE", enable_events=True, key=f"INSERT CHECKBOX||IN{i} 3"),
                        psg.Checkbox(text="SL", enable_events=True, key=f"INSERT CHECKBOX||IN{i} 4"),
                        psg.Checkbox(text="SR", enable_events=True, key=f"INSERT CHECKBOX||IN{i} 5"),
                        psg.Checkbox(text="BL", enable_events=True, key=f"INSERT CHECKBOX||IN{i} 6"),
                        psg.Checkbox(text="BR", enable_events=True, key=f"INSERT CHECKBOX||IN{i} 7"),
                    ],
                )

        asio_checkboxes = list()
        inner = list()
        checkbox_lists = ([] for _ in range(self.kind.num_strip))
        for i, checkbox_list in enumerate(checkbox_lists):
            if i < self.kind.phys_in:
                [step(checkbox_list, i + 1) for step in (add_insert_checkboxes,)]
                inner.append(psg.Frame(f"In#{i + 1}", checkbox_list))
            else:
                [step(checkbox_list, i + 1) for step in (add_insert_checkboxes,)]
                asio_checkboxes.append([psg.Frame(f"In#{i + 1}", checkbox_list)])
        asio_checkboxes.insert(0, inner)

        return psg.Frame("PATCH INSERT", asio_checkboxes)
