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
        return [[row0], [row1]]

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
        asio_checkboxes_in1, asio_checkboxes_in2, asio_checkboxes_in3, asio_checkboxes_in4, asio_checkboxes_in5 = (
            [] for _ in range(5)
        )
        for i, checkbox_list in enumerate(
            (
                asio_checkboxes_in1,
                asio_checkboxes_in2,
                asio_checkboxes_in3,
                asio_checkboxes_in4,
                asio_checkboxes_in5,
            )
        ):
            [step(checkbox_list, i + 1) for step in (add_asio_checkboxes,)]
            inner.append(psg.Frame(f"In#{i + 1}", checkbox_list))

        asio_checkboxes = [inner]
        return psg.Frame("PATCH ASIO Inputs to Strips", asio_checkboxes)
