# std vs
from vapoursynth import core
import vapoursynth as vs
import os
import functools
# vs func repos
try:
    import havsfunc
except ImportError:
    raise RuntimeError(
        "pvsfunc.PDeinterlacer: Required script havsfunc not found. "
        "https://github.com/HomeOfVapourSynthEvolution/havsfunc"
    )

# pip packages
from pyd2v import D2V


class PDeinterlacer:
    """
    PDeinterlacer (PHOENiX Deinterlacer)
    Deinterlaces a clip with the most optimal wrapping based on the sourcer.
    The clip will need to be loaded from PSourcer to work as it needs it's Props.
    """

    def __init__(self, clip, tff=True, kernel=None, kernel_args=None, debug=False):
        self.clip = clip
        self.tff = tff
        self.kernel = kernel
        self.kernel_args = kernel_args
        self.debug = debug
        # validate arguments
        if not isinstance(self.clip, vs.VideoNode):
            raise TypeError("pvsfunc.PDeinterlacer: This is not a clip")
        # set default kernel to QTGMC
        if not self.kernel:
            self.kernel = havsfunc.QTGMC
        # if kernel is QTGMC, set it's defaults
        if self.kernel == havsfunc.QTGMC:
            self.kernel_args = {
                # defaults
                **{
                    "FPSDivisor": 2,
                    "Preset": "Placebo",
                    "MatchPreset": "Placebo",
                    "MatchPreset2": "Placebo",
                    "TFF": self.tff,
                    "InputType": 0,
                    "SourceMatch": 3,
                    "Lossless": 2,
                    "Sharpness": 0.2,
                    "ShutterBlur": 0,
                    "ShutterAngleSrc": 0,
                    "ShutterAngleOut": 0,
                    "SBlurLimit": 0
                },
                # user configuration
                **dict(self.kernel_args or {})
            }
        self.props = self.clip.get_frame(0).props
        self.props = {k: v.decode("utf-8") if type(v) == bytes else v for k, v in self.props.items()}
        if self.props["PVSSourcer"] == "core.d2v.Source":
            self._d2v()
        elif self.props["PVSSourcer"] == "core.ffms2.Source":
            if kernel == havsfunc.QTGMC:
                kernel_args["FPSDivisor"] = 2  # only supporting same-rate fps atm
            self._ffms2()
        elif self.props["PVSSourcer"] == "core.imwri.Read":
            print("pvsfunc.PDeinterlacer: Warning: This source is a clip of images and cannot be deinterlaced.")
        else:
            raise ValueError(f"Unimplemented deinterlacer for Sourcer {self.props['PVSSourcer']}")
    
    def _d2v(self):
        """
        Very accurate deinterlacing using raw frame metadata to know what to
        deinterlace when necessary. It even fixes the frame rates of progressive
        streams and converts VFR to CFR when necessary.

        For MPEG2, this is as good as it gets in terms of using a deinterlacer.
        """
        # 1. create a clip from the output of the kernel deinterlacer
        deinterlaced_clip = self.kernel(self.clip, **self.kernel_args)
        fps_factor = deinterlaced_clip.fps.numerator / deinterlaced_clip.fps.denominator
        fps_factor = fps_factor / (self.clip.fps.numerator / self.clip.fps.denominator)
        if fps_factor != 1.0 and fps_factor != 2.0:
            raise ValueError(
                f"pvsfunc.PDeinterlacer: The deinterlacer kernel returned an unsupported frame-rate ({deinterlaced_clip.fps}). "
                "Only single-rate and double-rate is supported with PDeinterlacer at the moment."
            )
        # 2. deinterlace whats interlaced
        def _d(n, f, c, d, ff):
            if f.props["PVSFlagProgressiveFrame"]:
                # progressive frame, we don't need to do any deinterlacing to this frame
                # though we may need to duplicate it if double-rate fps output
                rc = core.std.Interleave([c] * ff) if ff > 1 else c
                return core.text.Text(
                    rc,
                    f" VOB: {f.props['PVSFlagVob']}:{f.props['PVSFlagCell']} - Frame #{n:,} - Untouched ",
                    alignment=1
                ) if self.debug else rc
            # interlaced frame, we need to use `d` (deinterlaced) frame.
            return core.text.Text(
                d,
                f" VOB: {f.props['PVSFlagVob']}:{f.props['PVSFlagCell']} - Frame #{n:,} - Deinterlaced! ",
                alignment=1
            ) if self.debug else d
        self.clip = core.std.FrameEval(
            deinterlaced_clip,
            functools.partial(
                _d,
                c=self.clip,
                d=deinterlaced_clip,
                ff=fps_factor
            ),
            prop_src=self.clip
        )
    
    def _ffms2(self):
        """
        Deinterlace using ffms2 (ffmpeg) using a basic FieldBased!=0 => QTGMC method
        """
        self.clip = core.std.FrameEval(
            self.clip,
            functools.partial(
                lambda n, f, c, d: (
                    core.text.Text(c, "Untouched Frame (_FieldBased=0)", alignment=1) if self.debug else c
                ) if f.props["_FieldBased"] == 0 else (
                    core.text.Text(d, "Deinterlaced Frame (via QTGMC)", alignment=1) if self.debug else d
                ),
                c=self.clip,
                d=self.kernel(self.clip, **self.kernel_args)
            ),
            prop_src=self.clip
        )
