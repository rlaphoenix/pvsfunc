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

    def __init__(self, clip, kernel=None, kernel_args=None, debug=False):
        self.clip = clip
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
                    "TFF": True,  # handle this automatically
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
        # set handler func based on Sourcer
        self.handler = None
        sourcer = self.clip.get_frame(0).props["PVSSourcer"].decode("utf-8")
        if sourcer == "core.d2v.Source":
            self.handler = self._d2v
        elif sourcer == "core.ffms2.Source":
            if self.kernel == havsfunc.QTGMC:
                kernel_args["FPSDivisor"] = 2  # only supporting same-rate fps atm
            self.handler = self._ffms2
        elif sourcer == "core.lsmas.LWLibavSource":
            if self.kernel == havsfunc.QTGMC:
                kernel_args["FPSDivisor"] = 2  # only supporting same-rate fps atm
            self.handler = self._lsmash
        elif sourcer == "core.imwri.Read":
            print("pvsfunc.PDeinterlacer: Warning: This source is a clip of images and cannot be deinterlaced.")
            self.handler = lambda c: c  # do nothing
        else:
            raise ValueError(f"Unimplemented deinterlacer for Sourcer {sourcer}")
        self.clip = self.handler(self.clip)
    
    def _get_kernel(self, clip):
        """
        Apply the deinterlacing kernel to the provided clip for both
        TFF and BFF output. The Kernel function will be provided a 
        True/False value to the "TFF" argument.
        """
        return (
            self.kernel(clip, **{**self.kernel_args, "TFF": True}),
            self.kernel(clip, **{**self.kernel_args, "TFF": False})
        )

    def _d2v(self, clip):
        """
        Very accurate deinterlacing using raw frame metadata to know what to
        deinterlace when necessary. It even fixes the frame rates of progressive
        streams and converts VFR to CFR when necessary.

        For MPEG2, this is as good as it gets in terms of using a deinterlacer.
        """
        # 1. create a clip from the output of the kernel deinterlacer
        deinterlaced_tff, deinterlaced_bff = self._get_kernel(clip)
        fps_factor = deinterlaced_tff.fps.numerator / deinterlaced_tff.fps.denominator
        fps_factor = fps_factor / (clip.fps.numerator / clip.fps.denominator)
        if fps_factor != 1.0 and fps_factor != 2.0:
            raise ValueError(
                f"pvsfunc.PDeinterlacer: The deinterlacer kernel returned an unsupported frame-rate ({deinterlaced_tff.fps}). "
                "Only single-rate and double-rate is supported with PDeinterlacer at the moment."
            )
        # 2. deinterlace whats interlaced
        def _d(n, f, c, d_tff, d_bff, ff):
            if f.props["PVSFlagProgressiveFrame"]:
                # progressive frame, we don't need to do any deinterlacing to this frame
                # though we may need to duplicate it if double-rate fps output
                rc = core.std.Interleave([c] * ff) if ff > 1 else c
                return core.text.Text(
                    rc,
                    f" VOB: {f.props['PVSFlagVob']}:{f.props['PVSFlagCell']} - Frame #{n:,} - Untouched ",
                    alignment=1
                ) if self.debug else rc
            # interlaced frame, we need to use `d_tff`/`d_bff` (deinterlaced) frame.
            return core.text.Text(
                d_tff if f.props["_FieldBased"] == 2 else d_bff,
                f" VOB: {f.props['PVSFlagVob']}:{f.props['PVSFlagCell']} - Frame #{n:,} - Deinterlaced! ",
                alignment=1
            ) if self.debug else (d_tff if f.props["_FieldBased"] == 2 else d_bff)
        return core.std.FrameEval(
            deinterlaced_tff,
            functools.partial(
                _d,
                c=clip,
                d_tff=deinterlaced_tff,
                d_bff=deinterlaced_bff,
                ff=fps_factor
            ),
            prop_src=clip
        )
    
    def _ffms2(self, clip):
        """
        Deinterlace using ffms2 (ffmpeg) using a basic FieldBased!=0 => QTGMC method
        """
        deinterlaced_tff, deinterlaced_bff = self._get_kernel(clip)
        return core.std.FrameEval(
            clip,
            functools.partial(
                lambda n, f, c, d_tff, d_bff: (
                    core.text.Text(c, "Untouched Frame (_FieldBased=0)", alignment=1) if self.debug else c
                ) if f.props["_FieldBased"] == 0 else (
                    core.text.Text(
                        d_tff if f.props["_FieldBased"] == 2 else d_bff,
                        "Deinterlaced Frame (via QTGMC)",
                        alignment=1
                    ) if self.debug else (d_tff if f.props["_FieldBased"] == 2 else d_bff)
                ),
                c=clip,
                d_tff=deinterlaced_tff,
                d_bff=deinterlaced_bff
            ),
            prop_src=clip
        )
    
    def _lsmash(self, clip):
        """
        Deinterlace using lsmas (lsmash) using a basic FieldBased!=0 => QTGMC method
        """
        return self._ffms2(clip)  # same method as ffms2
