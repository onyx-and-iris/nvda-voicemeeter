from typing import Union

import PySimpleGUI as psg

from . import util


class LabelSlider(psg.Frame):
    """Compound Label Slider Strip element"""

    def __init__(self, parent, i, param, range_=(0, 10), *args, **kwargs):
        self.parent = parent
        if param in ("AUDIBILITY", "DENOISER"):
            size = 7
        else:
            if psg.theme() == "HighContrast":
                size = 5
            else:
                size = 4
        layout = [
            [
                psg.Text(param.capitalize(), size=size),
                psg.Slider(
                    range=range_,
                    default_value=self.default_value(i, param),
                    resolution=0.1,
                    disable_number_display=True,
                    size=(12, 16),
                    expand_x=True,
                    enable_events=True,
                    orientation="horizontal",
                    key=f"STRIP {i}||SLIDER {param}",
                ),
            ]
        ]
        super().__init__(None, layout=layout, border_width=0, pad=0, *args, **kwargs)

    def default_value(self, i, param):
        target = getattr(self.parent.vm.strip[i], param.lower())
        if param in ("COMP", "GATE", "DENOISER"):
            return target.knob
        return target


class CompSlider(psg.Slider):
    """Compressor Slider element"""

    def __init__(self, vm, index, param):
        self.vm = vm
        self.index = index
        super().__init__(
            disable_number_display=True,
            expand_x=True,
            enable_events=True,
            orientation="horizontal",
            key=f"COMPRESSOR||SLIDER {param}",
            **self.default_params(param),
        )

    def default_params(self, param):
        match param:
            case "INPUT GAIN":
                return {
                    "range": (-24, 24),
                    "default_value": self.vm.strip[self.index].comp.gainin,
                    "resolution": 0.1,
                    "disabled": True,
                }
            case "RATIO":
                return {
                    "range": (1, 8),
                    "default_value": self.vm.strip[self.index].comp.ratio,
                    "resolution": 0.1,
                }
            case "THRESHOLD":
                return {
                    "range": (-40, -3),
                    "default_value": self.vm.strip[self.index].comp.threshold,
                    "resolution": 0.1,
                }
            case "ATTACK":
                return {
                    "range": (0, 200),
                    "default_value": self.vm.strip[self.index].comp.attack,
                    "resolution": 0.1,
                }
            case "RELEASE":
                return {
                    "range": (0, 5000),
                    "default_value": self.vm.strip[self.index].comp.release,
                    "resolution": 0.1,
                }
            case "KNEE":
                return {
                    "range": (0, 1),
                    "default_value": self.vm.strip[self.index].comp.knee,
                    "resolution": 0.01,
                }
            case "OUTPUT GAIN":
                return {
                    "range": (-24, 24),
                    "default_value": self.vm.strip[self.index].comp.gainout,
                    "resolution": 0.1,
                    "disabled": True,
                }

    @staticmethod
    def check_bounds(param, val):
        match param:
            case "RATIO":
                val = util.check_bounds(val, (1, 8))
            case "THRESHOLD":
                val = util.check_bounds(val, (-40, -3))
            case "ATTACK":
                val = util.check_bounds(val, (0, 200))
            case "RELEASE":
                val = util.check_bounds(val, (0, 5000))
            case "KNEE":
                val = util.check_bounds(val, (0, 1))
        return val


class GateSlider(psg.Slider):
    def __init__(self, vm, index, param):
        self.vm = vm
        self.index = index
        super().__init__(
            disable_number_display=True,
            expand_x=True,
            enable_events=True,
            orientation="horizontal",
            key=f"GATE||SLIDER {param}",
            **self.default_params(param),
        )

    def default_params(self, param):
        match param:
            case "THRESHOLD":
                return {
                    "range": (-60, -10),
                    "default_value": self.vm.strip[self.index].gate.threshold,
                    "resolution": 0.1,
                }
            case "DAMPING":
                return {
                    "range": (-60, -10),
                    "default_value": self.vm.strip[self.index].gate.damping,
                    "resolution": 0.1,
                }
            case "BPSIDECHAIN":
                return {
                    "range": (100, 4000),
                    "default_value": self.vm.strip[self.index].gate.bpsidechain,
                    "resolution": 1,
                }
            case "ATTACK":
                return {
                    "range": (0, 1000),
                    "default_value": self.vm.strip[self.index].gate.attack,
                    "resolution": 0.1,
                }
            case "HOLD":
                return {
                    "range": (0, 5000),
                    "default_value": self.vm.strip[self.index].gate.hold,
                    "resolution": 0.1,
                }
            case "RELEASE":
                return {
                    "range": (0, 5000),
                    "default_value": self.vm.strip[self.index].gate.release,
                    "resolution": 0.1,
                }

    @staticmethod
    def check_bounds(param, val):
        match param:
            case "THRESHOLD":
                val = util.check_bounds(val, (-60, -10))
            case "DAMPING MAX":
                val = util.check_bounds(val, (-60, -10))
            case "BPSIDECHAIN":
                val = util.check_bounds(val, (100, 4000))
            case "ATTACK":
                val = util.check_bounds(val, (0, 1000))
            case "HOLD":
                val = util.check_bounds(val, (0, 5000))
            case "RELEASE":
                val = util.check_bounds(val, (0, 5000))
        return val


class LabelSliderAdvanced(psg.Frame):
    """Compound Label Slider element for Advanced Comp|Gate"""

    def __init__(self, parent, index, param, slider_cls: Union[CompSlider, GateSlider], *args, **kwargs):
        label_map = {
            "DAMPING": "Damping Max",
            "BPSIDECHAIN": "BP Sidechain",
        }

        layout = [
            [
                psg.Text(label_map.get(param, param.title()), size=10),
                slider_cls(parent.vm, index, param),
            ]
        ]
        super().__init__(None, layout=layout, border_width=0, pad=0, *args, **kwargs)
