# std vs
from vapoursynth import core
import vapoursynth as vs
import os
import functools
# pip packages
from pyd2v import D2V
# pvsfunc
from pvsfunc.helpers import anti_file_prefix, get_mime_type, get_video_codec, get_d2v, calculate_par, calculate_aspect_ratio


CODEC_SOURCER_MAP = {
    "IMAGE": "core.imwri.Read",
    "V_MPEG1": "core.d2v.Source",
    "V_MPEG2": "core.d2v.Source",
    # codecs not listed here will default to `core.ffms2.Source`
}

SOURCER_ARGS_MAP = {
    "core.imwri.Read": {
        # disable the alpha channel as it often causes an incompatibility
        # with some functions due to the extra channel
        "alpha": False
    },
    "core.d2v.Source": {
        # ignore rff (pulldown flags) as we do not want it to interlace
        # the pulldown frames and end up giving us more work...
        "rff": False
    },
    "core.ffms2.Source": {
        # disable the alpha channel as it often causes an incompatibility
        # with some functions due to the extra channel
        "alpha": False
    }
}


class PSourcer:
    """
    PSourcer (PHOENiX Sourcer)
    Loads an input file path with the most optimal clip source based on the file.
    This is mainly a wrapper function for my other classes and functions of pvsfunc.
    The sourcer (and it's arguments) are based on my own personal opinions.
    -
    core.d2v.Source is used on videos that are supported by DGIndex v1.5.8
    core.ffms2.Source is used on everything else
    if DGDecNV ever gets linux support I will test it out and add support. Until then its dead to me.
    """

    def __init__(self, file_path, debug=False):
        if not hasattr(core, "d2v"):
            raise RuntimeError(
                "pvsfunc.PSourcer: Required plugin d2vsource for namespace 'd2v' not found. "
                "https://github.com/dwbuiten/d2vsource"
            )
        if not hasattr(core, "ffms2"):
            raise RuntimeError(
                "pvsfunc.PSourcer: Required plugin ffms2 for namespace 'ffms2' not found. "
                "https://github.com/FFMS/ffms2"
            )
        self.debug = debug
        self.clip = None
        self.file_path = anti_file_prefix(file_path)
        self.file_type = get_mime_type(self.file_path)
        self.video_codec = get_video_codec(self.file_path)
        if self.file_type.startswith("image/"):
            self.video_codec = "IMAGE"
        self.sourcer = self.get_sourcer(self.video_codec)
        # sourcer preparations
        if self.sourcer == "core.d2v.Source":
            # make sure a d2v file for this video exists
            self.file_path = get_d2v(self.file_path)
        # load video to clip using sourcer
        self.clip = eval(self.sourcer)(self.file_path, **SOURCER_ARGS_MAP[self.sourcer])
        # post sourcing preparations
        if self.sourcer == "core.d2v.Source":
            # ========================================================================= #
            #  Variable to Constant Frame-rate                                          #
            # ------------------------------------------------------------------------- #
            # Apply pulldown (if any) by duplicating frames rather than field to result #
            # in a Constant frame rate. Apply any duplication done to the list of flags #
            # as well.                                                                  #
            # ========================================================================= #
            # parse d2v file with pyd2v
            d2v = D2V(self.file_path)
            # get every frames' flag data, this contains information on displaying frames
            # add vob and cell number to each frames flag data as well
            flags = [f for l in [
                [dict(**y, vob=x["vob"], cell=x["cell"]) for y in x["flags"]] for x in d2v.data
            ] for f in l]
            # Get pulldown cycle
            # todo ; get an mpeg2 that uses Pulldown metadata (rff flags) that ISN'T Pulldown 2:3 to test math
            #        this math seems pretty far fetched, if we can somehow obtain the Pulldown x:x:...
            #        string that mediainfo can get, then calculating it can be much easier and more efficient.
            pulldown_cycle = [n for n,f in enumerate(flags) if f["tff"] and f["rff"]]
            if not pulldown_cycle:
                pulldown_cycle = 0  # a 0 would be better than an empty list
            else:
                # pair every 2 frame indexes together
                pulldown_cycle = list(zip(pulldown_cycle[::2], pulldown_cycle[1::2]))
                # subtract the right index with the left index to calculate the cycle
                pulldown_cycle = [r - l for l,r in pulldown_cycle]
                # get the most common cycle (+1), interlaced sections in variable scan-type content messes up the
                # results, so the only way around it is to get the most common entry.
                pulldown_cycle = max(set(pulldown_cycle), key=pulldown_cycle.count) + 1
            # set various data used for debugging (if debug enabled)
            if self.debug:
                coded_pictures = len(flags)
                progressive_percent = (sum(1 for f in flags if f["progressive_frame"]) / len(flags)) * 100
                pulldown_count = sum(1 for f in flags if f["progressive_frame"] and f["rff"] and f["tff"])
            # fix flag items if variable scan type
            if not all(x["progressive_frame"] for x in flags):
                # video is not all progressive content, meaning it is either:
                # - entirely interlaced
                # - mix of progressive and interlaced sections
                # 1. fix the frame rate of the progressive sections by applying it's pulldown
                #    we fix it by duplicating the pulldown specified frames rather than as fields
                pulldown_indexes = [n for n,f in enumerate(flags) if f["progressive_frame"] and f["rff"] and f["tff"]]
                if pulldown_indexes:
                    self.clip = core.std.DuplicateFrames(clip=self.clip, frames=pulldown_indexes)
                # 2. apply the changes above to the flag list to match the fixed clip
                flags = [f for sl in [(
                    [f,dict(**{**f, **{"progressive_frame": True, "rff": False, "tff": False}})]
                    if f["progressive_frame"] and f["rff"] and f["tff"] else [f]
                ) for f in flags] for f in sl]
            else:
                # video is fully progressive, but the frame rate needs to be fixed.
                # core.d2v.Source loads the video while ignoring pulldown flags, but
                # it will still set the metadata frame rate of the clip to NTSC/PAL.
                # but if Pulldown was used, then the frame rate would be wrong. Let's
                # fix that ourselves.
                if pulldown_cycle:
                    self.clip = core.std.AssumeFPS(
                        self.clip,
                        fpsnum=self.clip.fps.numerator - (self.clip.fps.numerator / pulldown_cycle),
                        fpsden=self.clip.fps.denominator
                    )
            # ========================================================================= #
            #  Store flags in each frame's props                                        #
            # ------------------------------------------------------------------------- #
            # This allows scripts to utilise each frame's correct prop without having   #
            # to re-do the flag VFR->CFR fixing and vob/cell mapping. You can view a    #
            # list of the props available at any time with core.text.FrameProps().      #
            # All props will be either an int, int-style bool, or string.               #
            # ========================================================================= #
            def set_flag_props(n, f, c, fl):
                for k, v in fl[n].items():
                    if isinstance(v, bool):
                        v = 1 if v else 0
                    if isinstance(v, bytes):
                        v = v.decode("utf-8")
                    c = core.std.SetFrameProp(c, **{
                        ("intval" if isinstance(v, int) else "data"): v
                    }, prop=f"PVSFlag{k.title().replace('_', '')}")
                return c[n]
            self.clip = core.std.FrameEval(
                self.clip,
                functools.partial(
                    set_flag_props,
                    c=self.clip,
                    fl=flags
                ),
                prop_src=self.clip
            )
            vob_indexes = [index for _, index in {f["vob"]: n for n, f in enumerate(flags)}.items()]
            vob_indexes = [f"{(0 if n == 0 else (vob_indexes[n-1] + 1))}-{i}" for n,i in enumerate(vob_indexes)]
            self.clip = core.std.SetFrameProp(self.clip, prop="PVSVobIdIndexes", data=" ".join(vob_indexes))
            if self.debug:
                # fps
                fps = self.clip.fps
                if self.clip.fps.numerator == 25:
                    fps = "PAL"
                elif self.clip.fps.numerator == 30000:
                    fps = "NTSC"
                elif self.clip.fps.numerator == 24:
                    fps = "FILM"
                # aspect ratio
                ar = d2v.settings['Aspect_Ratio']
                ar_n = [int(x) for x in ar.split(':')]
                par = calculate_par(self.clip.width, self.clip.height, *ar_n)
                sar = calculate_aspect_ratio(self.clip.width, self.clip.height)
                self.clip = core.text.Text(
                    self.clip,
                    " " + (" \n ".join([
                        f"{os.path.basename(self.file_path)}",
                        f"{fps}, Loaded with {str(self.sourcer)}",
                        f"- {coded_pictures:,} coded pictures, which {progressive_percent:.2f}% of are Progressive",
                        f"- {pulldown_count:,} frames are asking for pulldown{f' which occurs every {pulldown_cycle} frames' if pulldown_cycle else ''}",
                        f"- {coded_pictures + pulldown_count:,} total frames after pulldown flags are honored",
                        f"DAR: {ar}  SAR: {sar}  PAR: {par}"
                    ])) + " ",
                    alignment=7
                )
        # set various props that the user may find helpful
        for k, v in [
            ("FilePath", self.file_path),
            ("Codec", self.video_codec),
            ("Sourcer", str(self.sourcer))
        ]:
            # why the fuck is there no SetFrameProps, come on...
            # +1: https://github.com/vapoursynth/vapoursynth/issues/559
            self.clip = core.std.SetFrameProp(self.clip, prop=f"PVS{k}", data=v)

    @staticmethod
    def get_sourcer(video_codec):
        """Get clip sourcer function based on video codec"""
        if video_codec not in CODEC_SOURCER_MAP:
            # default to FFMPEG-based sourcer for wide compatibility
            return "core.ffms2.Source"
        return CODEC_SOURCER_MAP[video_codec]
