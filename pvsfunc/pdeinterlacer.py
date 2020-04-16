# std vs
from vapoursynth import core
import vapoursynth as vs
import os
import functools
# vs func repos
import havsfunc
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
        self.props = {k: v.decode("utf-8") if type(v) == bytes else v for k,v in self.props.items()}
        if self.props["PVSSourcer"] == "core.d2v.Source":
            self._d2v()
        elif self.props["PVSSourcer"] == "core.ffms2.Source":
            if kernel == havsfunc.QTGMC:
                kernel_args["FPSDivisor"] = 2  # only supporting same-rate fps atm
            self._ffms2()
        else:
            raise ValueError(f"Unimplemented deinterlacer for Sourcer {self.props['PVSSourcer']}")
    
    def _d2v(self):
        """
        Very accurate deinterlacing using raw frame metadata to know what to
        deinterlace when necessary. It even fixes the frame rates of progressive
        streams and converts VFR to CFR when necessary.

        For MPEG2, this is as good as it gets in terms of using a deinterlacer.
        """
        # Get D2V object
        self.d2v = D2V(self.props["PVSFilePath"])
        # Get every frames' flag data, this contains information on displaying frames
        flags = [f for l in [x["flags"] for x in self.d2v.data] for f in l]
        # Get percentage of progressive frames
        progressive_percent = (sum(1 for x in flags if x["progressive_frame"]) / len(flags))*100
        # Get pulldown information
        pulldown_frames = [n for n,f in enumerate(flags) if f["progressive_frame"] and f["rff"] and f["tff"]]
        # todo ; get an mpeg2 that uses Pulldown metadata (rff flags) that ISN'T Pulldown 2:3 to test math
        #        this math seems pretty far fetched, if we can somehow obtain the Pulldown x:x:...
        #        string that mediainfo can get, then calculating it can be much easier and more efficient.
        pulldown_cycle = [n for n,f in enumerate(flags) if not f["tff"] and not f["rff"]]
        if pulldown_cycle:
            pulldown_cycle = list(zip(pulldown_cycle[::2], pulldown_cycle[1::2]))
            pulldown_cycle = [r - l for l,r in pulldown_cycle]
            pulldown_cycle = max(set(pulldown_cycle), key=pulldown_cycle.count) + 1  # most common entry + 1
        else:
            pulldown_cycle = None

        if progressive_percent != 100.0:
            # video is not all progressive content, meaning it is either:
            # - entirely interlaced
            # - mix of progressive and interlaced sections
            # interlaced sections fps == 30000/1001
            # progressive sections fps <= 30000/1001 (or == if they used Pulldown 1:1 for some reason)
            # 1. fix the frame rate of the progressive sections by applying it's pulldown (without interlacing) to make the video CFR
            #    if this isn't done, then the frame rate of the progressive sections will be 30000/1001 but the content itself will not be
            if pulldown_frames:
                self.clip = core.std.DuplicateFrames(clip=self.clip, frames=pulldown_frames)
            # 2. also apply this frame rate fix to the flag list so that each flag can be properly accessed by index
            pulldown_flags = []
            for flag in flags:
                pulldown_flags.append(flag)
                if flag["progressive_frame"] and flag["rff"] and flag["tff"]:
                    pulldown_flags.append({"progressive_frame": True, "rff": False, "tff": False})
            # 3. create a clip from the output of the kernel deinterlacer
            deinterlaced_clip = self.kernel(self.clip, **self.kernel_args)
            double_rate = self.clip.fps.numerator * 2 == deinterlaced_clip.fps.numerator
            # 4. create a format clip, used for metadata of final clip
            format_clip = core.std.BlankClip(
                clip=self.clip,
                length=len(pulldown_flags) * (2 if double_rate else 1),
                fpsnum=self.clip.fps.numerator * (2 if double_rate else 1),
                fpsden=self.clip.fps.denominator
            )
            # 5. deinterlace whats interlaced
            def _d(n, f, c, d, fl, dr):
                if fl[int(n / 2) if dr else n]["progressive_frame"]:
                    # progressive frame, we don't need to do any deinterlacing to this frame
                    # though we may need to duplicate it if double-rate fps output
                    rc = core.std.Interleave([c, c]) if dr else c
                    return core.text.Text(rc, "\n\n\n\n\n\n (Untouched Frame) ", alignment=7) if self.debug else rc
                # interlaced frame, we need to use `d` (deinterlaced) frame.
                return core.text.Text(d, "\n\n\n\n\n\n ! Deinterlaced Frame ! ", alignment=7) if self.debug else d
            self.clip = core.std.FrameEval(
                format_clip,
                functools.partial(
                    _d,
                    c=self.clip,
                    d=deinterlaced_clip,
                    fl=pulldown_flags,
                    dr=double_rate
                ),
                prop_src=self.clip
            )
        else:
            # video is entirely progressive without a hint of interlacing in sight
            # however, it needs it's FPS to be fixed. rff=False with core.d2v.Source
            # resulted in it returning with the FPS set to 30000/1001, let's revert that
            # back to whatever it should be based on its pulldown cycle
            if pulldown_cycle:
                self.clip = core.std.AssumeFPS(
                    self.clip,
                    fpsnum=self.clip.fps.numerator - (self.clip.fps.numerator / pulldown_cycle),
                    fpsden=self.clip.fps.denominator
                )
        
        if self.debug:
            fps = self.clip.fps
            if self.clip.fps.numerator == 25:
                fps = "PAL"
            elif self.clip.fps.numerator == 30000:
                fps = "NTSC"
            elif self.clip.fps.numerator == 24:
                fps = "FILM"
            self.clip = core.text.Text(
                self.clip,
                " " + (" \n ".join([
                    f"{os.path.basename(self.props['PVSFilePath'])}",
                    f"{fps}, Loaded with {self.props['PVSSourcer']}",
                    f"- {len(flags)} coded pictures, which {progressive_percent:.2f}% of are Progressive",
                    f"- {len(pulldown_frames)} frames are asking for pulldown{f' which occurs every {pulldown_cycle} frames' if pulldown_cycle else ''}",
                    f"- {len(flags) + len(pulldown_frames)} total frames after pulldown flags are honored"
                ])) + " ",
                alignment=7
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