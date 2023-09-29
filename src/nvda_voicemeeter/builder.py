import PySimpleGUI as psg

from . import util
from .compound import LabelSlider


class Builder:
    """Responsible for building the Window layout"""

    def __init__(self, window):
        self.window = window
        self.vm = self.window.vm
        self.kind = self.vm.kind

    def run(self) -> list:
        menu = [[self.make_menu()]]

        layout0 = []
        if self.kind.name == "basic":
            steps = (
                self.make_tab0_row0,
                self.make_tab0_row1,
                self.make_tab0_row5,
            )
        else:
            steps = (
                self.make_tab0_row0,
                self.make_tab0_row1,
                self.make_tab0_row2,
                self.make_tab0_row3,
                self.make_tab0_row4,
                self.make_tab0_row5,
            )
        for step in steps:
            layout0.append([step()])

        layout1_1 = []
        steps = (self.make_tab1_button_rows,)
        for step in steps:
            layout1_1.append([step()])
        layout1_2 = []
        steps = (self.make_tab1_slider_rows,)
        for step in steps:
            layout1_2.append([step()])

        layout2_1 = []
        steps = (self.make_tab2_button_rows,)
        for step in steps:
            layout2_1.append([step()])
        layout2_2 = []
        steps = (self.make_tab2_slider_rows,)
        for step in steps:
            layout2_2.append([step()])

        layout3_1 = []
        steps = (self.make_tab3_button_rows,)
        for step in steps:
            layout3_1.append([step()])
        layout3_2 = []
        steps = (self.make_tab3_slider_rows,)
        for step in steps:
            layout3_2.append([step()])

        def _make_inner_tabgroup(layouts, identifier) -> psg.TabGroup:
            inner_layout = []
            for i, tabname in enumerate(("buttons", "sliders")):
                inner_layout.append([psg.Tab(tabname.capitalize(), layouts[i], key=f"tab||{identifier}||{tabname}")])
            return psg.TabGroup(
                inner_layout,
                change_submits=True,
                enable_events=True,
                key=f"tabgroup||{identifier}",
            )

        def _make_tabs(identifier) -> psg.Tab:
            match identifier:
                case "Settings":
                    return psg.Tab("Settings", layout0, key="tab||Settings")
                case "Physical Strip":
                    tabgroup = _make_inner_tabgroup((layout1_1, layout1_2), identifier)
                case "Virtual Strip":
                    tabgroup = _make_inner_tabgroup((layout2_1, layout2_2), identifier)
                case "Buses":
                    tabgroup = _make_inner_tabgroup((layout3_1, layout3_2), identifier)
            return psg.Tab(identifier, [[tabgroup]], key=f"tab||{identifier}")

        tabs = []
        for tab in util.get_tabs_labels():
            tabs.append(_make_tabs(tab))

        tab_group = psg.TabGroup([tabs], change_submits=True, enable_events=True, key="tabgroup")

        return [[menu], [tab_group]]

    def make_menu(self) -> psg.Menu:
        menu_def = [
            [
                "&Voicemeeter",
                [
                    "Restart Audio Engine::MENU",
                    "Save Settings::MENU",
                    "Load Settings::MENU",
                    "Load Settings on Startup ::MENU",
                ],
            ],
        ]
        return psg.Menu(menu_def, key="menus")

    def make_tab0_row0(self) -> psg.Frame:
        """tab0 row0 represents hardware ins"""

        def add_physical_device_opts(layout):
            devices = util.get_input_device_list(self.vm)
            devices.append("- remove device selection -")
            layout.append(
                [
                    psg.ButtonMenu(
                        f"IN {i + 1}",
                        size=(6, 3),
                        menu_def=["", devices],
                        key=f"HARDWARE IN||{i + 1}",
                    )
                    for i in range(self.kind.phys_in)
                ]
            )

        hardware_in = []
        [step(hardware_in) for step in (add_physical_device_opts,)]
        return psg.Frame("Hardware In", hardware_in)

    def make_tab0_row1(self) -> psg.Frame:
        """tab0 row1 represents hardware outs"""

        def add_physical_device_opts(layout):
            if self.kind.name == "basic":
                num_outs = self.kind.phys_out + self.kind.virt_out
            else:
                num_outs = self.kind.phys_out
            layout.append(
                [
                    psg.ButtonMenu(
                        f"A{i + 1}",
                        size=(6, 3),
                        menu_def=["", util.get_output_device_list(i, self.vm)],
                        key=f"HARDWARE OUT||A{i + 1}",
                    )
                    for i in range(num_outs)
                ]
            )

        hardware_out = []
        [step(hardware_out) for step in (add_physical_device_opts,)]
        return psg.Frame("Hardware Out", hardware_out)

    def make_tab0_row2(self) -> psg.Frame:
        """tab0 row2 represents patch asio inputs to strips"""

        def add_asio_checkboxes(layout, i):
            nums = list(range(99))
            layout.append(
                [
                    psg.Spin(
                        nums,
                        initial_value=self.window.cache["asio"][
                            f"ASIO CHECKBOX||{util.get_asio_checkbox_index(0, i)}"
                        ],
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
                        initial_value=self.window.cache["asio"][
                            f"ASIO CHECKBOX||{util.get_asio_checkbox_index(1, i)}"
                        ],
                        size=2,
                        enable_events=True,
                        key=f"ASIO CHECKBOX||IN{i} 1",
                    )
                ],
            )

        inner = []
        asio_checkboxlists = ([] for _ in range(self.kind.phys_out))
        for i, checkbox_list in enumerate(asio_checkboxlists):
            [step(checkbox_list, i + 1) for step in (add_asio_checkboxes,)]
            inner.append(psg.Frame(f"In#{i + 1}", checkbox_list))

        asio_checkboxes = [inner]
        return psg.Frame("PATCH ASIO Inputs to Strips", asio_checkboxes)

    def make_tab0_row3(self) -> psg.Frame:
        """tab0 row3 represents patch composite"""

        def add_physical_device_opts(layout):
            outputs = util.get_patch_composite_list(self.kind)
            layout.append(
                [
                    psg.ButtonMenu(
                        f"PC{i + 1}",
                        size=(6, 2),
                        menu_def=["", outputs],
                        key=f"PATCH COMPOSITE||PC{i + 1}",
                    )
                    for i in range(self.kind.composite)
                ]
            )

        hardware_out = []
        [step(hardware_out) for step in (add_physical_device_opts,)]
        return psg.Frame("PATCH COMPOSITE", hardware_out)

    def make_tab0_row4(self) -> psg.Frame:
        """tab0 row4 represents patch insert"""

        def add_insert_checkboxes(layout, i):
            if i <= self.kind.phys_in:
                [
                    layout.append(
                        [
                            psg.Checkbox(
                                text=channel,
                                default=self.window.cache["insert"][
                                    f"INSERT CHECKBOX||{util.get_insert_checkbox_index(self.kind, j, i)}"
                                ],
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
                            default=self.window.cache["insert"][
                                f"INSERT CHECKBOX||{util.get_insert_checkbox_index(self.kind, j, i)}"
                            ],
                            enable_events=True,
                            key=f"INSERT CHECKBOX||IN{i} {j}",
                        )
                        for j, channel in enumerate(("LEFT", "RIGHT", "C", "LFE", "SL", "SR", "BL", "BR"))
                    ],
                )

        asio_checkboxes = []
        inner = []
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

    def make_tab0_row5(self) -> psg.Frame:
        """tab0 row5 represents advanced settings"""

        return psg.Frame(
            "ADVANCED SETTINGS",
            [
                [
                    psg.Button(
                        "ADVANCED SETTINGS",
                        size=(20, 2),
                        key="ADVANCED SETTINGS",
                    )
                ],
            ],
            key="ADVANCED SETTINGS FRAME",
        )

    def make_tab1_button_row(self, i) -> psg.Frame:
        """tab1 row represents a strip's outputs (A1-A5, B1-B3)"""

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
                ],
            )
            layout.append(
                [
                    psg.Button("Mono", size=(6, 2), key=f"STRIP {i}||MONO"),
                    psg.Button("Solo", size=(6, 2), key=f"STRIP {i}||SOLO"),
                    psg.Button("Mute", size=(6, 2), key=f"STRIP {i}||MUTE"),
                ],
            )

        outputs = []
        [step(outputs) for step in (add_strip_outputs,)]
        return psg.Frame(self.window.cache["labels"][f"STRIP {i}||LABEL"], outputs, key=f"STRIP {i}||LABEL")

    def make_tab1_button_rows(self) -> psg.Frame:
        layout = [[self.make_tab1_button_row(i)] for i in range(self.kind.phys_in)]
        return psg.Frame(None, layout, border_width=0)

    def make_tab1_slider_row(self, i) -> psg.Frame:
        def add_gain_slider(layout):
            layout.append(
                [
                    psg.Text("Gain"),
                    psg.Slider(
                        range=(-60, 12),
                        default_value=self.vm.strip[i].gain,
                        resolution=0.1,
                        disable_number_display=True,
                        expand_x=True,
                        enable_events=True,
                        disabled=True,
                        orientation="horizontal",
                        key=f"STRIP {i}||SLIDER GAIN",
                    ),
                ]
            )

        def add_param_sliders(layout):
            layout.append([LabelSlider(self.window, i, param) for param in util.get_slider_params(i, self.kind)])

        def add_limit_slider(layout):
            layout.append(
                [
                    psg.Text("Limit"),
                    psg.Slider(
                        range=(-40, 12),
                        default_value=self.vm.strip[i].limit,
                        resolution=1,
                        disable_number_display=True,
                        expand_x=True,
                        enable_events=True,
                        orientation="horizontal",
                        key=f"STRIP {i}||SLIDER LIMIT",
                    ),
                ]
            )

        layout = []
        steps = (add_gain_slider, add_param_sliders)
        if self.kind.name in ("banana", "potato"):
            steps += (add_limit_slider,)
        [step(layout) for step in steps]
        return psg.Frame(self.window.cache["labels"][f"STRIP {i}||LABEL"], layout, key=f"STRIP {i}||LABEL||SLIDER")

    def make_tab1_slider_rows(self) -> psg.Frame:
        layout = [[self.make_tab1_slider_row(i)] for i in range(self.kind.phys_in)]
        return psg.Frame(None, layout, border_width=0)

    def make_tab2_button_row(self, i) -> psg.Frame:
        """tab2 row represents a strip's outputs (A1-A5, B1-B3)"""

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
            if i == self.kind.phys_in + 1:
                layout.append(
                    [
                        psg.Button("K", size=(6, 2), key=f"STRIP {i}||MONO"),
                        psg.Button("Solo", size=(6, 2), key=f"STRIP {i}||SOLO"),
                        psg.Button("Mute", size=(6, 2), key=f"STRIP {i}||MUTE"),
                    ],
                )
            else:
                layout.append(
                    [
                        psg.Button("MC", size=(6, 2), key=f"STRIP {i}||MONO"),
                        psg.Button("Solo", size=(6, 2), key=f"STRIP {i}||SOLO"),
                        psg.Button("Mute", size=(6, 2), key=f"STRIP {i}||MUTE"),
                    ],
                )

        outputs = []
        [step(outputs) for step in (add_strip_outputs,)]
        return psg.Frame(
            self.window.cache["labels"][f"STRIP {i}||LABEL"],
            outputs,
            key=f"STRIP {i}||LABEL",
        )

    def make_tab2_button_rows(self) -> psg.Frame:
        layout = [
            [self.make_tab2_button_row(i)] for i in range(self.kind.phys_in, self.kind.phys_in + self.kind.virt_in)
        ]
        return psg.Frame(None, layout, border_width=0)

    def make_tab2_slider_row(self, i) -> psg.Frame:
        def add_gain_slider(layout):
            layout.append(
                [
                    psg.Text("Gain"),
                    psg.Slider(
                        range=(-60, 12),
                        default_value=self.vm.strip[i].gain,
                        resolution=0.1,
                        disable_number_display=True,
                        expand_x=True,
                        enable_events=True,
                        disabled=True,
                        orientation="horizontal",
                        key=f"STRIP {i}||SLIDER GAIN",
                    ),
                ]
            )

        def add_param_sliders(layout):
            if self.kind.name in ("basic", "banana"):
                for param in util.get_slider_params(i, self.kind):
                    layout.append([LabelSlider(self.window, i, param, range_=(-12, 12))])
            else:
                layout.append(
                    [
                        LabelSlider(self.window, i, param, range_=(-12, 12))
                        for param in util.get_slider_params(i, self.kind)
                    ]
                )

        def add_limit_slider(layout):
            layout.append(
                [
                    psg.Text("Limit"),
                    psg.Slider(
                        range=(-40, 12),
                        default_value=self.vm.strip[i].limit,
                        resolution=1,
                        disable_number_display=True,
                        expand_x=True,
                        enable_events=True,
                        orientation="horizontal",
                        key=f"STRIP {i}||SLIDER LIMIT",
                    ),
                ]
            )

        layout = []
        steps = (add_gain_slider, add_param_sliders)
        if self.kind.name in ("banana", "potato"):
            steps += (add_limit_slider,)
        [step(layout) for step in steps]
        return psg.Frame(
            self.window.cache["labels"][f"STRIP {i}||LABEL"],
            layout,
            key=f"STRIP {i}||LABEL||SLIDER",
        )

    def make_tab2_slider_rows(self) -> psg.Frame:
        layout = [
            [self.make_tab2_slider_row(i)] for i in range(self.kind.phys_in, self.kind.phys_in + self.kind.virt_in)
        ]
        return psg.Frame(None, layout, border_width=0)

    def make_tab3_button_row(self, i) -> psg.Frame:
        """tab3 row represents bus composite toggle"""

        def add_strip_outputs(layout):
            params = ["MONO", "EQ", "MUTE"]
            if self.kind.name == "basic":
                params.remove("EQ")
            busmodes = [util._bus_mode_map[mode] for mode in util.get_bus_modes(self.vm)]
            layout.append(
                [
                    *[
                        psg.Button(
                            param.capitalize(),
                            size=(6, 2),
                            key=f"BUS {i}||{param}",
                        )
                        for param in params
                    ],
                    psg.ButtonMenu(
                        "BUSMODE",
                        size=(12, 2),
                        menu_def=["", busmodes],
                        key=f"BUS {i}||MODE",
                    ),
                ]
            )

        outputs = []
        [step(outputs) for step in (add_strip_outputs,)]
        return psg.Frame(
            self.window.cache["labels"][f"BUS {i}||LABEL"],
            outputs,
            key=f"BUS {i}||LABEL",
        )

    def make_tab3_button_rows(self) -> psg.Frame:
        layout = [[self.make_tab3_button_row(i)] for i in range(self.kind.num_bus)]
        return psg.Frame(None, layout, border_width=0)

    def make_tab3_slider_row(self, i) -> psg.Frame:
        def add_gain_slider(layout):
            layout.append(
                [
                    psg.Text("Gain"),
                    psg.Slider(
                        range=(-60, 12),
                        default_value=self.vm.bus[i].gain,
                        resolution=0.1,
                        disable_number_display=True,
                        expand_x=True,
                        enable_events=True,
                        disabled=True,
                        orientation="horizontal",
                        key=f"BUS {i}||SLIDER GAIN",
                    ),
                ]
            )

        outputs = []
        [step(outputs) for step in (add_gain_slider,)]
        return psg.Frame(self.window.cache["labels"][f"BUS {i}||LABEL"], outputs, key=f"BUS {i}||LABEL||SLIDER")

    def make_tab3_slider_rows(self) -> psg.Frame:
        layout = [[self.make_tab3_slider_row(i)] for i in range(self.kind.num_bus)]
        return psg.Frame(None, layout, border_width=0)
