import PySimpleGUI as psg

from .util import (
    get_asio_checkbox_index,
    get_input_device_list,
    get_insert_checkbox_index,
    get_patch_composite_list,
)


class Builder:
    """Responsible for building the Window layout"""

    def __init__(self, window):
        self.window = window
        self.vm = self.window.vm
        self.kind = self.vm.kind

    def run(self) -> list:
        layout0 = []
        if self.kind.name == "basic":
            steps = (self.make_tab0_row0,)
        else:
            steps = (self.make_tab0_row0, self.make_tab0_row1, self.make_tab0_row2, self.make_tab0_row3)
        for step in steps:
            layout0.append([step()])

        layout1 = []
        steps = (self.make_tab1_rows,)
        for step in steps:
            layout1.append([step()])

        layout2 = []
        steps = (self.make_tab2_rows,)
        for step in steps:
            layout2.append([step()])

        tab1 = psg.Tab("Settings", layout0, key="settings")
        tab2 = psg.Tab("Physical Strips", layout1, key="physical strip")
        tab3 = psg.Tab("Virtual Strips", layout2, key="virtual strip")
        tab_group = psg.TabGroup([[tab1, tab2, tab3]], change_submits=True, key="tabs")

        return [[tab_group]]

    def make_tab0_row0(self) -> psg.Frame:
        """row0 represents hardware outs"""

        def add_physical_device_opts(layout):
            devices = get_input_device_list(self.vm)
            devices.append("- remove device selection -")
            if self.kind.name == "basic":
                num_outs = self.kind.phys_out + self.kind.virt_out
            else:
                num_outs = self.kind.phys_out
            layout.append(
                [
                    psg.ButtonMenu(
                        f"A{i + 1}",
                        size=(6, 3),
                        menu_def=["", devices],
                        key=f"HARDWARE OUT||A{i + 1}",
                    )
                    for i in range(num_outs)
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

    def make_tab1_row(self, i) -> psg.Frame:
        def add_strip_outputs(layout):
            layout.append(
                [
                    psg.Button(
                        f"A{j + 1}" if j < self.kind.phys_out else f"B{j - self.kind.phys_out + 1}",
                        size=(4, 2),
                        key=f"STRIP {i}||A{j + 1}"
                        if j < self.kind.phys_out
                        else f"STRIP {i}||B{j - self.kind.phys_out + 1}",
                    )
                    for j in range(self.kind.phys_out + self.kind.virt_out)
                ]
            )

        outputs = list()
        [step(outputs) for step in (add_strip_outputs,)]
        return psg.Frame(self.vm.strip[i].label, outputs)

    def make_tab1_rows(self) -> psg.Frame:
        layout = [[self.make_tab1_row(i)] for i in range(self.kind.phys_in)]
        return psg.Frame(None, layout, border_width=0)

    def make_tab2_row(self, i) -> psg.Frame:
        def add_strip_outputs(layout):
            layout.append(
                [
                    psg.Button(
                        f"A{j + 1}" if j < self.kind.phys_out else f"B{j - self.kind.phys_out + 1}",
                        size=(4, 2),
                        key=f"STRIP {i}||A{j + 1}"
                        if j < self.kind.phys_out
                        else f"STRIP {i}||B{j - self.kind.phys_out + 1}",
                    )
                    for j in range(self.kind.phys_out + self.kind.virt_out)
                ]
            )

        outputs = list()
        [step(outputs) for step in (add_strip_outputs,)]
        return psg.Frame(self.vm.strip[i].label, outputs)

    def make_tab2_rows(self) -> psg.Frame:
        layout = [[self.make_tab1_row(i)] for i in range(self.kind.phys_in, self.kind.phys_in + self.kind.virt_in)]
        return psg.Frame(None, layout, border_width=0)
