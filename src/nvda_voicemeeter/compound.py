import PySimpleGUI as psg


class LabelSlider(psg.Frame):
    """Compound Label Slider Strip element"""

    def __init__(self, parent, i, param, range_=(0, 10), *args, **kwargs):
        self.parent = parent
        if param in ("AUDIBILITY", "DENOISER"):
            size = 7
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
                    "key": f"COMPRESSOR||SLIDER {param}",
                }
            case "RATIO":
                return {
                    "range": (1, 8),
                    "default_value": self.vm.strip[self.index].comp.ratio,
                    "resolution": 0.1,
                    "key": f"COMPRESSOR||SLIDER {param}",
                }
            case "THRESHOLD":
                return {
                    "range": (-40, -3),
                    "default_value": self.vm.strip[self.index].comp.threshold,
                    "resolution": 0.1,
                    "key": f"COMPRESSOR||SLIDER {param}",
                }
            case "ATTACK":
                return {
                    "range": (0, 200),
                    "default_value": self.vm.strip[self.index].comp.attack,
                    "resolution": 0.1,
                    "key": f"COMPRESSOR||SLIDER {param}",
                }
            case "RELEASE":
                return {
                    "range": (0, 5000),
                    "default_value": self.vm.strip[self.index].comp.release,
                    "resolution": 0.1,
                    "key": f"COMPRESSOR||SLIDER {param}",
                }
            case "KNEE":
                return {
                    "range": (0, 1),
                    "default_value": self.vm.strip[self.index].comp.knee,
                    "resolution": 0.01,
                    "key": f"COMPRESSOR||SLIDER {param}",
                }
            case "OUTPUT GAIN":
                return {
                    "range": (-24, 24),
                    "default_value": self.vm.strip[self.index].comp.gainout,
                    "resolution": 0.01,
                    "disabled": True,
                    "key": f"COMPRESSOR||SLIDER {param}",
                }


class LabelSliderCompressor(psg.Frame):
    """Compound Label Slider Compressor element"""

    def __init__(self, parent, index, param, *args, **kwargs):
        layout = [
            [
                psg.Text(param.capitalize(), size=8),
                CompSlider(parent.vm, index, param),
            ]
        ]
        super().__init__(None, layout=layout, border_width=0, pad=0, *args, **kwargs)
