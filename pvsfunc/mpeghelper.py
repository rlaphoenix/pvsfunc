# std vs
from vapoursynth import core  # this may give a linter error, ignore
# std py
import os
import functools
# vs func repos
import havsfunc
# pypi dependencies
from pymediainfo import MediaInfo

class MpegHelper():

    def __init__(self,
        file_path,
        rff=True,
        debug=False
    ):
        ## init
        self.debug = debug
        if self.debug:
            # debugging will use printhook to print various debugging values
            from . import printhook
        file_ext = file_path.lower().split('.')[-1]
        meta_path = file_path
        source = "ffms2"
        ## if it's a d2v file, use inner mpeg path and set source as d2v
        if file_ext == "d2v":
            source = "d2v"
            with open(file_path, "r") as f:
                # video filepath is always on line 3
                meta_path = [l.strip() for i,l in enumerate(f) if i==2][0]
            if "/" not in meta_path and "\\" not in meta_path:
                # convert video_path to absolute path if relative
                # pymediainfo needs absolute path
                meta_path = os.path.join(os.path.dirname(file_path), meta_path)
        ## Get metadata
        self.meta, self.codec = self.get_metadata(meta_path)
        ## If it's and MPEG-1 or MPEG-2 and not using a d2v file, raise exception
        if self.codec == "MPEG-1" or self.codec == "MPEG-2" and file_ext != "d2v":
            raise Exception(f"MpegHelper: file_path is an {self.codec} video file, create a .d2v file for it using DGIndex, and use that as file_path instead.")
        ## Load clip based on `source`
        self.check_plugin(source)
        if source == "d2v":
            self.clip = core.d2v.Source(file_path, rff=rff)
            if not rff and str(self.clip.fps) == "30000/1001":
                # for some reason rff=false still returns 30000/1001 and wrong duration, hacky fix
                self.clip = core.std.AssumeFPS(
                    self.clip,
                    fpsnum=self.meta.framerate_num,  # todo ; when num/den fps isnt detected by MediaInfo, this panics
                    fpsden=self.meta.framerate_den
                )
        else:
            self.clip = core.ffms2.Source(file_path, alpha=False)  # alpha plane is stupidly unnecessary
        # print some information on the metadata
        log = [
            f"File path: \"{file_path}\"",
            f"{source} / {self.clip.width}x{self.clip.height} @ {self.clip.fps} FPS / {self.meta.other_display_aspect_ratio[0]} DAR, {self.get_aspect_ratio(self.clip.width, self.clip.height)} SAR / {self.meta.scan_type}, {self.meta.scan_order} / {self.clip.format.name}"
        ]
        if self.debug:
            log.append("[!] Debug mode enabled")
        print("\n".join(log))
    
    def deinterlace(self):
        self.check_plugin("vivtc")
        def vfm(clip, tff):
            return core.vivtc.VFM(
                clip,
                # Sets the field order of the clip
                # 0=BFF, 1=TFF
                order=1 if tff else 0,
                # Sets the field to match from. This is the field that VFM will take from the current frame in case of p or n matches
                # 0=BFF, 1=TFF, 2=Same as order, 3=Opposite of order
                field=2,
                # Sets the matching mode or strategy to use. Plain 2-way matching (option 0) is the safest of all the options
                # http://www.vapoursynth.com/doc/plugins/vivtc.html
                mode=0
            )
        def deinterlace_(n, f, o):
            if f.props["_FieldBased"] == 0:
                return core.text.Text(o, "Original Frame (FieldBased=0)") if self.debug else o
            vfm_c = vfm(o, tff=f.props["_FieldBased"] == 2)
            def decomb(n, f, vfm_c_p, tff):
                if f.props["_Combed"] > 0:
                    q = havsfunc.QTGMC(
                        vfm_c_p,
                        FPSDivisor=2,
                        Preset="Placebo",
                        MatchPreset="Placebo",              # must be same or worse than Preset
                        MatchPreset2="Placebo",             # must be same or worse than Preset
                        TFF=tff,
                        InputType=0,                        # 0 is best, 3 is best for Progressive/Burned In
                        SourceMatch=3,
                        Lossless=2,
                        Sharpness=0.2,
                        ShutterBlur=0,
                        ShutterAngleSrc=0,
                        ShutterAngleOut=0,
                        SBlurLimit=0
                    )
                    return core.text.Text(q, "Deinterlacer: QTGMC (VFM fallback)") if self.debug else q
                return core.text.Text(vfm_c, "Deinterlacer: VFM") if self.debug else vfm_c
            return core.std.FrameEval(
                vfm_c,
                functools.partial(
                    decomb,
                    vfm_c_p=vfm_c,
                    tff=f.props["_FieldBased"] == 2
                ),
                prop_src=vfm_c
            )
        self.clip = core.std.FrameEval(
            self.clip,
            functools.partial(
                deinterlace_,
                o=self.clip
            ),
            prop_src=self.clip
        )
    
    def decimate(self,
        cycle=5,
        offsets=[0, 1, 3, 4],  #[0, 2, 3, 4],
        skip_checks=False
    ):
        """
        Efficiently and safely decimate (inverse-telecine/ivtc) a clip.
        """
        if not skip_checks and str(self.clip.fps) != "30000/1001":
            print("decimate: Video isn't 30000/1001, so it's unsure if the video is actually telecined, skipping. (force with skip_checks=True)")
            return False
        print(f"decimate: (cycle={cycle}, offsets={offsets}, skip_checks={skip_checks})")
        # vdecimate uses similarity checks to find the duplicates in the cycle
        # in my experience it is stupidly inaccurate, unless you can't for some
        # reason, use SelectEvery to IVTC instead
        # core.vivtc.VDecimate(self.clip, cycle=5)
        self.clip = core.std.SelectEvery(self.clip, cycle, offsets)

    def depillarbox(self,
        aspect_ratio,  # Example: 4/3 to crop to 4:3, 16/9 to crop to 16:9
        direction=0,   # 0 = landscape, 1 = portrait
        offset=0       # crop in x pixels more or less than evaluated area
    ):
        """
        Crop out pillarboxing by automatically evaluating the area
        based on a centered aspect ratio
        """
        area = (self.clip.width - (self.clip.height * aspect_ratio)) / 2
        self.clip = core.std.CropRel(
            self.clip,
            left=area + offset if direction == 0 else 0,
            top=0 if direction == 0 else area + offset,
            right=area - offset if direction == 0 else 0,
            bottom=0 if direction == 0 else area - offset
        )

    ## Helpers
    @staticmethod
    def check_plugin(attribute: str):
        if not hasattr(core, attribute):
            raise RuntimeError(f"MpegHelper: required plugin '{attribute}' is not installed.")

    @staticmethod
    def get_metadata(file_path: str) -> tuple:
        meta = [x for x in MediaInfo.parse(file_path).tracks if x.track_type == "Video"][0]
        codec = meta.format.upper()
        if codec == "MPEG VIDEO":
            codec = f"MPEG-{meta.format_version.upper().replace('VERSION ', '')}"
        return (meta, codec)

    @staticmethod
    def get_aspect_ratio(width: int, height: int) -> str:
        def gcd(a, b):
            """The GCD (greatest common divisor) is the highest number that evenly divides both width and height."""
            return a if b == 0 else gcd(b, a % b)
        r = gcd(width, height)
        return f"{int(width / r)}:{int(height / r)}"
