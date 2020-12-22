import functools

import mvsfunc
from vapoursynth import core, VideoNode, ColorFamily, RGB24

try:
    import havsfunc
except ImportError:
    raise RuntimeError(
        "pvsfunc.PDeinterlacer: Required script havsfunc not found. "
        "https://github.com/HomeOfVapourSynthEvolution/havsfunc"
    )


class PDeinterlacer:
    """
    PDeinterlacer (PHOENiX Deinterlacer)
    Deinterlaces a clip with the most optimal wrapping based on the sourcer.
    The clip will need to be loaded from PSourcer to work as it needs it's Props.
    """

    def __init__(self, clip, kernel=None, kernel_args=None, debug=False):
        self.clip = clip
        self.kernel = kernel
        self.kernel_args = kernel_args or {}
        self.debug = debug
        # validate arguments
        if not isinstance(self.clip, VideoNode):
            raise TypeError("pvsfunc.PDeinterlacer: This is not a clip")
        # set default kernel to QTGMC
        if not self.kernel:
            self.kernel = havsfunc.QTGMC
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

    def _get_kernel(self, clip) -> tuple:
        """
        Apply the deinterlacing kernel to the provided clip for both
        TFF and BFF output. The Kernel function will be provided a 
        True/False value to the "TFF" argument if any.

        Expecting a TFF argument (case-insensitive), it must be present.
        If the function truly doesn't need it (what??) then wrap it in a lambda, e.g.
        lambda clip, TFF: yourWeirdFunc(clip)

        Returns 2 clips, one for TFF operations, and one for BFF operations
        """
        field_order_arg = [x for x in self.kernel.__code__.co_varnames if x.lower() == "tff"]
        if field_order_arg:
            return (
                self.kernel(clip, **{**self.kernel_args, field_order_arg[0]: True}),
                self.kernel(clip, **{**self.kernel_args, field_order_arg[0]: False})
            )
        clip = self.kernel(clip, **self.kernel_args)
        return clip, clip

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
        fps_factor = int(fps_factor)

        # 2. ensure the color families between tff and bff kernel uses match
        if deinterlaced_tff.format.id != deinterlaced_bff.format.id:
            raise ValueError(
                f"pvsfunc.PDeinterlacer: The kernel used supplied different color space outputs between TFF and BFF usage."
            )

        # 3. deinterlace whats interlaced
        def _d(n, f, c, d_tff, d_bff, ff):
            # compile debug information to print if requested
            debug_info = None
            if self.debug:
                debug_info = f"VOB: {f.props['PVSFlagVob']}:{f.props['PVSFlagCell']} - Frame #{n:,}"
            # progressive frame, simply skip deinterlacing
            if f.props["PVSFlagProgressiveFrame"]:
                rc = core.std.Interleave([c] * ff) if ff > 1 else c  # duplicate if not a single-rate fps output
                if rc.format.id != d_tff.format.id:
                    rc = core.resize.Point(rc, format=d_tff.format.id)
                return core.text.Text(rc, f" {debug_info} - Progressive ", alignment=1) if self.debug else rc
            # interlaced frame, use deinterlaced clip, d_tff if TFF (2) or d_bff if BFF (1)
            rc = {0: c, 1: d_bff, 2: d_tff}[f.props["_FieldBased"]]
            if self.debug:
                field_order = {0: "Progressive", 1: "BFF", 2: "TFF"}[f.props["_FieldBased"]]
                return core.text.Text(rc, f" {debug_info} - Deinterlaced ({field_order} ", alignment=1)
            return rc
        
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
    
    @classmethod
    def RGBtoYUV(cls, R, G, B):

        def RGBtoY(R, G, B):
            return ((0.257 * R) + (0.504 * G) + (0.098 * B) + 16)
        
        def RGBtoU(R, G, B):
            return (-(0.148 * R) - (0.291 * G) + (0.439 * B) + 128)
        
        def RGBtoV(R, G, B):
            return ((0.439 * R) - (0.368 * G) - (0.071 * B) + 128)
        
        return [RGBtoY(R, G, B), RGBtoU(R, G, B), RGBtoV(R, G, B)]

    @classmethod
    def VoidWeave(cls, clip, tff, color, bob=False) -> VideoNode:
        """
        Weaves a 255(rgb) #00ff00(hex) green as the 2nd field of every field.
        The purpose of this would be for machine learning in-painting over
        the green rows with interpreted pixel data for machine learning
        deinterlacing.

        This function will convert clip's color-space to RGB24. It needs to
        for creating a clip with linear 255 RGB green. Otherwise the machine
        learning code may not pick up the rows green as the correct green
        and fail. The color space has to match the void green clip and the
        actual field clip to be able to weave them together.
        """
        # colors
        # help needed ; figure out a way to get this working without having to convert colorspace at all
        # the if color family == YUV RGBtoYUV call is always NOP until then
        if clip.format.name != "RGB24":
            clip = core.resize.Point(clip, format=RGB24)
        if clip.format.color_family.name == "YUV":
            color = cls.RGBtoYUV(*color)
        # weave
        clip = core.std.SeparateFields(clip, tff=tff)
        clip = core.std.Interleave([
            clip,
            core.std.BlankClip(clip, color=color, keep=0)
        ])
        clip = core.std.DoubleWeave(clip, tff=tff)
        clip = core.std.SelectEvery(clip, cycle=2, offsets=0)
        # handle bobbing, keep every deinterlaced "field" if true
        if bob:
            # vertically align every even (2nd) field with every odd (1st) field
            # by adding a 1px row of black pixels on the top, and removing from the bottom
            odd = core.std.SelectEvery(clip, cycle=2, offsets=0)
            even = core.std.SelectEvery(clip, cycle=2, offsets=1)
            even = core.std.AddBorders(even, top=1, color=color)
            even = core.std.Crop(even, bottom=1)
            return core.std.Interleave([odd, even])
        return core.std.SelectEvery(clip, cycle=2, offsets=0)
