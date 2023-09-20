import PySimpleGUI as psg


class LabelSlider(psg.Frame):
    """Compound Label Slider element"""

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
