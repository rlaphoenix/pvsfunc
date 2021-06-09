import functools

import vapoursynth as vs
from vapoursynth import core


class PDeinterlacer:
    """
    PDeinterlacer (PHOENiX Deinterlacer).
    Deinterlaces a clip with the most optimal wrapping based on the sourcer.
    The clip will need to be loaded from PSourcer to work as it needs it's Props.
    """

    def __init__(self, clip, kernel, kernel_args=None, debug=False):
        if not kernel:
            raise ValueError("A deinterlacing kernel is required")
        self.clip = clip
        self.kernel = kernel
        self.kernel_args = kernel_args or {}
        self.debug = debug
        # validate arguments
        if not isinstance(self.clip, vs.VideoNode):
            raise TypeError("This is not a clip")
        # set handler func based on Sourcer
        sourcer = self.clip.get_frame(0).props["PVSSourcer"].decode("utf-8")
        if sourcer == "core.imwri.Read":
            # todo ; add support for deinterlacing image data (somehow)
            print("Warning: This source is a clip of images and cannot be deinterlaced")
        elif sourcer in ["core.lsmas.LWLibavSource"]:
            if "FPSDivisor" in kernel_args and kernel_args["FPSDivisor"] != 2:
                # todo ; ideally make this unnecessary
                raise ValueError(
                    "%s only supports QTGMC single-rate output (FPSDivisor=2)" % sourcer
                )
        self.handler = {
            "core.lsmas.LWLibavSource": self._lsmash,
            "core.imwri.Read": lambda c: c  # NOP
        }.get(sourcer)
        if self.handler is None:
            raise NotImplementedError("No sourcer is defined for the given media stream")
        self.clip = self.handler(self.clip)

    def _get_kernel(self, clip) -> tuple:
        """
        Apply the deinterlacing kernel to the provided clip for both TFF and BFF output.

        The Kernel function will be provided a True/False value to the "TFF". A "TFF" argument on the kernel
        function is required, but is not case sensitive. If the function truly doesn't need a field order specification
        then wrap it in a lambda, e.g. `lambda clip, tff: yourWeirdFunc(clip)`

        Returns 2 clips, one for TFF operations, and one for BFF operations.
        """
        field_order_arg = [x for x in self.kernel.__code__.co_varnames if x.lower() == "tff"]
        if field_order_arg:
            return (
                self.kernel(clip, **{**self.kernel_args, field_order_arg[0]: True}),
                self.kernel(clip, **{**self.kernel_args, field_order_arg[0]: False})
            )
        clip = self.kernel(clip, **self.kernel_args)
        return clip, clip

    def _lsmash(self, clip):
        """
        Deinterlace clips that are loaded with core.lsmas.LWLibavSource.
        It only deinterlaces frames that need to be deinterlaced. It entirely skips frames marked as progressive.
        However, this isn't as perfect as the _d2v method, as it doesn't manually use the frame index data. Instead
        it assumes LWLibavSource has done it correctly, and assumes it did it at all.

        Typically used for AVC/MPEG-4/H.264 or HEVC/H.265 video sources.
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
