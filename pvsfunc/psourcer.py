import functools
import itertools
import mimetypes
import os
from typing import Union

import vapoursynth as vs
from pyd2v import D2V
from vapoursynth import core

from pvsfunc.helpers import anti_file_prefix, get_video_codec, get_d2v, fps_reset, calculate_par, \
    calculate_aspect_ratio

CODEC_SOURCER_MAP = {
    "IMAGE": "core.imwri.Read",
    "V_MPEG1": "core.d2v.Source",
    "V_MPEG2": "core.d2v.Source",
}

SOURCER_ARGS_MAP = {
    "core.imwri.Read": {
        # disable the alpha channel as it often causes an incompatibility
        # with some functions due to the extra channel
        "alpha": False,
        "firstnum": 0
    },
    "core.d2v.Source": {
        # ignore rff (pulldown flags) as we do not want it to interlace
        # the pulldown frames and end up giving us more work...
        "rff": False
    },
    "core.lsmas.LWLibavSource": {
        "stream_index": -1,  # get best stream in terms of res
        "dr": False  # enabling this seemed to cause issues on Linux for me
    }
}


class PSourcer:
    """
    PSourcer (PHOENiX Sourcer).
    Loads an input file path with the most optimal clip source based on the file.
    This is mainly a wrapper function for my other classes and functions of pvsfunc.
    The sourcer (and it's arguments) are based on my own personal opinions.
    -
    core.d2v.Source is used on videos that are supported by DGIndex v1.5.8
    core.lsmas.LWLibavSource is used on everything else
    if DGDecNV ever gets linux support I will test it out and add support. Until then its dead to me.
    """

    def __init__(self, file_path, debug=False):
        if not hasattr(core, "d2v"):
            raise RuntimeError(
                "pvsfunc.PSourcer: Required plugin d2vsource for namespace 'd2v' not found. "
                "https://github.com/dwbuiten/d2vsource"
            )
        if not hasattr(core, "lsmas"):
            raise RuntimeError(
                "pvsfunc.PSourcer: Required plugin lsmas for namespace 'lsmas' not found. "
                "https://github.com/VFR-maniac/L-SMASH-Works"
            )
        self.debug = debug
        self.clip = None
        self.file_path = anti_file_prefix(file_path)
        # if unknown mime type, assume video, I don't want to constantly update a whitelist
        self.file_type = mimetypes.guess_type(self.file_path)[0] or "video"
        self.file_type = self.file_type.split("/")[0]
        if self.file_type not in ("video", "image"):
            raise ValueError("pvsfunc.PSourcer: Only Video or Image files are supported. (%s)" % self.file_type)
        self.video_codec = get_video_codec(self.file_path)
        # core.d2v.Source specific
        self.d2v = None
        if self.video_codec == -1:
            raise ValueError("pvsfunc.PSourcer: File path supplied does not exist")
        if self.video_codec == -2:
            raise ValueError("pvsfunc.PSourcer: File supplied does not have a Video or Image track")
        if self.file_type == "image":
            # we do this after get_video_codec so it checks if an image
            # track actually exists, and not just an empty image container
            self.video_codec = "IMAGE"
        self.sourcer = CODEC_SOURCER_MAP.get(self.video_codec, "core.lsmas.LWLibavSource")
        # sourcer preparations
        if self.sourcer == "core.d2v.Source":
            # make sure a d2v file for this video exists
            self.file_path = get_d2v(self.file_path)
        elif self.sourcer == "core.lsmas.LWLibavSource":
            # destroy the container-set fps
            self.file_path = fps_reset(self.file_path)
        # load video to clip using sourcer
        while True:
            try:
                func = core
                for split in self.sourcer.replace("core.", "").split("."):
                    func = getattr(func, split)
                self.clip = func(self.file_path, **SOURCER_ARGS_MAP[self.sourcer])
                break
            except vs.Error as e:
                if self.sourcer == "core.imwri.Read" and "Read: No files matching the given pattern exist" in str(e):
                    # default uses first num of 0, maybe the user's first image is 1, let's not annoy them
                    # and just dynamically handle that
                    if SOURCER_ARGS_MAP[self.sourcer]["firstnum"] == 1:
                        raise
                    SOURCER_ARGS_MAP[self.sourcer]["firstnum"] = 1
                else:
                    raise
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
            self.d2v = D2V(self.file_path)
            # get every frames' flag data, this contains information on displaying frames
            # add vob and cell number to each frames flag data as well
            flags = [[dict(**y, vob=d["vob"], cell=d["cell"]) for y in d["flags"]] for d in self.d2v.data]
            flags = list(itertools.chain.from_iterable(flags))  # flatten list of lists
            # Get pulldown cycle
            # todo ; get an mpeg2 that uses Pulldown metadata (rff flags) that ISN'T Pulldown 2:3 to test math
            #        this math seems pretty far fetched, if we can somehow obtain the Pulldown x:x:...
            #        string that mediainfo can get, then calculating it can be much easier and more efficient.
            pulldown_cycle = [n for n, f in enumerate(flags) if f["tff"] and f["rff"]]
            if not pulldown_cycle or pulldown_cycle == [0]:
                pulldown_cycle = 0  # a 0 would be better than an empty list/list with only a 0
            else:
                # pair every 2 frame indexes together
                pulldown_cycle = list(zip(pulldown_cycle[::2], pulldown_cycle[1::2]))
                # subtract the right index with the left index to calculate the cycle
                pulldown_cycle = [right - left for left, right in pulldown_cycle]
                # get the most common cycle (+1), interlaced sections in variable scan-type content messes up the
                # results, so the only way around it is to get the most common entry.
                pulldown_cycle = max(set(pulldown_cycle), key=pulldown_cycle.count) + 1
            # set various data used for debugging (if debug enabled)
            coded_pictures = None
            progressive_percent = None
            pulldown_count = None
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
                pulldown_indexes = [n for n, f in enumerate(flags) if f["progressive_frame"] and f["rff"] and f["tff"]]
                if pulldown_indexes:
                    self.clip = core.std.DuplicateFrames(clip=self.clip, frames=pulldown_indexes)
                # 2. apply the changes above to the flag list to match the fixed clip
                flags = [f for sl in [(
                    [f, dict(**{**f, **{"progressive_frame": True, "rff": False, "tff": False}})]
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
            self.clip = core.std.FrameEval(
                self.clip,
                functools.partial(
                    self._set_flag_props,
                    c=self.clip,
                    fl=flags
                ),
                prop_src=self.clip
            )
            vob_indexes = [index for _, index in {f["vob"]: n for n, f in enumerate(flags)}.items()]
            vob_indexes = [
                "%d-%d" % ((0 if n == 0 else (vob_indexes[n - 1] + 1)), i) for n, i in enumerate(vob_indexes)
            ]
            self.clip = core.std.SetFrameProp(self.clip, prop="PVSVobIdIndexes", data=" ".join(vob_indexes))
            if self.debug:
                # fps
                fps = self.clip.fps
                if self.clip.fps.numerator == 25 and self.clip.fps.denominator == 1:
                    fps = "PAL"
                elif self.clip.fps.numerator == 30000 and self.clip.fps.denominator == 1001:
                    fps = "NTSC"
                elif self.clip.fps.numerator == 24 and self.clip.fps.denominator == 1:
                    fps = "FILM"
                # aspect ratio
                dar = self.d2v.settings["Aspect_Ratio"]
                par = calculate_par(self.clip.width, self.clip.height, *[int(x) for x in dar.split(":")])
                sar = calculate_aspect_ratio(self.clip.width, self.clip.height)
                self.clip = core.text.Text(
                    self.clip,
                    " " + (" \n ".join([
                        os.path.basename(self.file_path),
                        "Loaded with %s" % self.sourcer,
                        "- {:,d} coded pictures, which {:.2f}% of are Progressive".format(
                            coded_pictures, progressive_percent
                        ),
                        "- {:,d} frames are asking for pulldown{:s}".format(
                            pulldown_count,
                            ' which occurs every {:,d} frames'.format(pulldown_cycle) if pulldown_cycle else ''
                        ),
                        "- {:,d} total frames after pulldown flags are honored".format(coded_pictures + pulldown_count),
                        "DAR: %s  SAR: %s  PAR: %s  FPS: %s" % (dar, sar, par, fps)
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
            self.clip = core.std.SetFrameProp(self.clip, prop="PVS" + k, data=v)

    @classmethod
    def change_chroma_loc(cls, clip: vs.VideoNode, new_loc: Union[int, str], verbose: bool = False):
        """
        Change the Chroma Location of the clip.
        It's a possible case for the chroma location to be incorrect, you can use this to fix it's location
        An incorrect chroma location value is often the reason for chroma bleed.
        :param clip: Clip to change chroma location of
        :param new_loc: New chroma location
        :param verbose: Print the current and new locations that is changed on each frame
        """
        if new_loc is None:
            return clip
        if isinstance(new_loc, str):
            new_loc = {
                "top-left": 2, "top": 3,
                "left": 0, "center": 1,
                "bottom-left": 4, "bottom": 5
            }.get(new_loc.replace(" ", "-").replace("_", "-"))
        if not isinstance(new_loc, int) or (isinstance(new_loc, int) and 0 > new_loc > 5):
            raise ValueError(
                "pvsfunc.change_chroma_loc: new_loc must be an int between 0..5, "
                "or a string denoting the location, e.g. top-left, center, bottom..."
            )
        clip = core.resize.Point(clip, chromaloc=new_loc)
        if verbose:
            return core.text.Text(clip, "ChromaLoc: %d" % new_loc, 3)
        return clip

    @staticmethod
    def _set_flag_props(n, f, c, fl):
        for key, value in fl[n].items():
            if isinstance(value, bool):
                value = 1 if value else 0
            if isinstance(value, bytes):
                value = value.decode("utf-8")
            c = core.std.SetFrameProp(c, **{
                ("intval" if isinstance(value, int) else "data"): value
            }, prop="PVSFlag%s" % key.title().replace("_", ""))
        return c[n]
