import PySimpleGUI as psg

from .util import (
    get_asio_checkbox_index,
    get_input_device_list,
    get_insert_checkbox_index,
    get_patch_composite_list,
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
            steps = (self.make_tab0_row0,)
        else:
            steps = (self.make_tab0_row0, self.make_tab0_row1, self.make_tab0_row2, self.make_tab0_row3)
        for step in steps:
            layout.append([step()])

        # dummy layouts
        layout2 = [
            [
                psg.Button(
                    f"1",
                    size=(6, 3),
                    key=f"ZA BUTTON||1",
                )
            ]
        ]

        layout3 = [
            [
                psg.Button(
                    f"2",
                    size=(6, 3),
                    key=f"ZA BUTTON||2",
                )
            ]
        ]

        tab1 = psg.Tab("settings", layout)
        tab2 = psg.Tab("physical strips", layout2)
        tab3 = psg.Tab("virtual strips", layout3)
        Tg = psg.TabGroup([[tab1, tab2, tab3]])

        return [[Tg]]

    def make_tab0_row0(self) -> psg.Frame:
        """row0 represents hardware outs"""

        def add_physical_device_opts(layout):
            devices = get_input_device_list(self.vm)
            devices.append("- remove device selection -")
            layout.append(
                [
                    psg.ButtonMenu(
                        f"A{i + 1}",
                        size=(6, 3),
                        menu_def=["", devices],
                        key=f"HARDWARE OUT||A{i + 1}",
                    )
                    for i in range(self.kind.phys_out)
                ]
            )

        hardware_out = list()
        [step(hardware_out) for step in (add_physical_device_opts,)]
        return psg.Frame("Hardware Out", hardware_out)

    def make_tab0_row1(self) -> psg.Frame:
        """row1 represents patch asio inputs to strips"""

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

    def make_tab0_row2(self) -> psg.Frame:
        """row2 represents patch composite"""

        def add_physical_device_opts(layout):
            outputs = get_patch_composite_list(self.vm.kind)
            layout.append(
                [
                    psg.ButtonMenu(
                        f"PC{i + 1}",
                        size=(6, 2),
                        menu_def=["", outputs],
                        key=f"PATCH COMPOSITE||PC{i + 1}",
                    )
                    for i in range(self.kind.phys_out)
                ]
            )

        hardware_out = list()
        [step(hardware_out) for step in (add_physical_device_opts,)]
        return psg.Frame("PATCH COMPOSITE", hardware_out)

    def make_tab0_row3(self) -> psg.Frame:
        """row3 represents patch insert"""

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
