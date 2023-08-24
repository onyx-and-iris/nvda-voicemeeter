import PySimpleGUI as psg

from .util import (
    get_asio_checkbox_index,
    get_input_device_list,
    get_insert_checkbox_index,
)


class Builder:
    """Responsible for building the Window layout"""

    def __init__(self, window, vm):
        self.window = window
        self.vm = vm
        self.kind = self.vm.kind

    def run(self) -> list:
        layout = []
        if self.kind.name == "basic":
            steps = (self.make_row0,)
        else:
            steps = (self.make_row0, self.make_row1, self.make_row2)
        for step in steps:
            layout.append([step()])
        return layout

    def make_row0(self) -> psg.Frame:
        def add_physical_device_opts(layout):
            devices = get_input_device_list(self.vm)
            devices.append("- remove device selection -")
            layout.append(
                [
                    psg.ButtonMenu(
                        f"A{i}",
                        size=(6, 3),
                        menu_def=["", [f"{device}" for device in devices]],
                        key=f"HARDWARE OUT||A{i}",
                    )
                    for i in range(1, self.kind.phys_out + 1)
                ]
            )

        hardware_out = list()
        [step(hardware_out) for step in (add_physical_device_opts,)]
        return psg.Frame("Hardware Out", hardware_out)

    def make_row1(self) -> psg.Frame:
        def add_asio_checkboxes(layout, i):
            nums = list(range(99))
            layout.append(
                [
                    psg.Spin(
                        nums,
                        initial_value=self.vm.patch.asio[get_asio_checkbox_index(0, i)].get(),
                        size=2,
                        enable_events=True,
                        key=f"ASIO CHECKBOX||IN{i} 0",
                    )
                ],
            )
            layout.append(
                [
                    psg.Spin(
                        nums,
                        initial_value=self.vm.patch.asio[get_asio_checkbox_index(1, i)].get(),
                        size=2,
                        enable_events=True,
                        key=f"ASIO CHECKBOX||IN{i} 1",
                    )
                ],
            )

        inner = list()
        asio_checkboxlists = ([] for _ in range(self.kind.phys_out))
        for i, checkbox_list in enumerate(asio_checkboxlists):
            [step(checkbox_list, i + 1) for step in (add_asio_checkboxes,)]
            inner.append(psg.Frame(f"In#{i + 1}", checkbox_list))

        asio_checkboxes = [inner]
        return psg.Frame("PATCH ASIO Inputs to Strips", asio_checkboxes)

    def make_row2(self) -> psg.Frame:
        def add_insert_checkboxes(layout, i):
            if i <= self.kind.phys_in:
                [
                    layout.append(
                        [
                            psg.Checkbox(
                                text=channel,
                                default=self.vm.patch.insert[get_insert_checkbox_index(self.kind, j, i)].on,
                                enable_events=True,
                                key=f"INSERT CHECKBOX||IN{i} {j}",
                            )
                        ],
                    )
                    for j, channel in enumerate(("LEFT", "RIGHT"))
                ]
            else:
                layout.append(
                    [
                        psg.Checkbox(
                            text=channel,
                            default=self.vm.patch.insert[get_insert_checkbox_index(self.kind, j, i)].on,
                            enable_events=True,
                            key=f"INSERT CHECKBOX||IN{i} {j}",
                        )
                        for j, channel in enumerate(("LEFT", "RIGHT", "C", "LFE", "SL", "SR", "BL", "BR"))
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
