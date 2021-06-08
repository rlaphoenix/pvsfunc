import functools
import itertools
import mimetypes
import os
from typing import Union, Optional, List

import vapoursynth as vs
from pyd2v import D2V
from vapoursynth import core

from pvsfunc.helpers import anti_file_prefix, get_video_codec, get_d2v, fps_reset, calculate_par, \
    calculate_aspect_ratio, list_select_every, group_by_int

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

    def __init__(self, file_path, d2v_vst_vfr_mode: (Union[int, bool], Optional[List[int]]) = False, debug=False):
        """
        Convenience wrapper for loading video files to clip variables. It's purpose is to load an input file path
        with the most optimal clip source based on the file. For example for an MPEG-2 video file (e.g. DVD file) will
        load using core.d2v.Source (and generate an optimized d2v if needed too!), whereas an MPEG-4/AVC/H.264 video
        will load using core.lsmas.LWLibavSource.

        :param file_path: Input file path, can be any extension and can include `file://` prefix.
        :param d2v_vst_vfr_mode: Mode to use when matching frame rates for VFR (specifically VST) input.
            False : Duplicate the progressive frames that have `rff flags`, No frame drops. This is
                the operation that was done prior to this parameter being added. This is the safest option, it wont
                drop any frames, but you will end up with duplicate frames in the progressive sections.
            True : Decimate interlaced sections with a Pulldown cycle that matches the one using by the Progressive RFF
                sections. It's offsets will default to delete the middle (if cycle is an odd number, otherwise last)
                frame number of every cycle. You can do: (True, [0, 1, 2, 3]) to use a custom offsets list.
            tuple of (int/bool, list[int]) : Decimate interlaced sections with a manual (cycle, offsets list).
                A value of (False, list[int]) is an error, but a value of (True, list[int]) is fine, see above.
            NOTE: For the modes that decimate frames, it doesn't do any checks in regards to cycle resets when
                entering a new VOB id/cell like PDecimate does. It also doesn't decimate using SelectEvery or cycles.
                It decimates simply by deleting every nth frame where n is the value you chose (explained above).
        :param debug: Print various information and metadata about the loaded clip.
        """
        self.debug = debug
        self.clip = None
        self.file_path = anti_file_prefix(file_path)
        if not isinstance(d2v_vst_vfr_mode, tuple):
            d2v_vst_vfr_mode = (d2v_vst_vfr_mode, None)

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
            if not hasattr(core, "d2v"):
                raise RuntimeError(
                    "pvsfunc.PSourcer: Required plugin d2vsource for namespace 'd2v' not found. "
                    "https://github.com/dwbuiten/d2vsource"
                )
            # make sure a d2v file for this video exists
            self.file_path = get_d2v(self.file_path)
        elif self.sourcer == "core.lsmas.LWLibavSource":
            if not hasattr(core, "lsmas"):
                raise RuntimeError(
                    "pvsfunc.PSourcer: Required plugin lsmas for namespace 'lsmas' not found. "
                    "https://github.com/VFR-maniac/L-SMASH-Works"
                )
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
            self.d2v = D2V(self.file_path)

            # Get all flag data, this contains information on displaying frames/fields.
            # Each flag in the list can be either a progressive (full) frame, or a field (half) frame.
            # So unless the video is 100% interlaced or progressive, the flags count wont match the video FPS.
            flags = [
                dict(**y, vob=d["vob"], cell=d["cell"])  # flag from data, vob & cell from data
                for d in self.d2v.data
                for y in d["flags"]
            ]

            # Get Pulldown Cycle
            # todo ; get an mpeg2 that uses Pulldown metadata (rff flags) that ISN'T Pulldown 2:3 to test math
            #        this math seems pretty far fetched, if we can somehow obtain the Pulldown x:x:...
            #        string that mediainfo can get, then calculating it can be much easier and more efficient.
            pulldown_cycle = [n for n, f in enumerate(flags) if f["rff"]]
            pulldown_cycle = pulldown_cycle[::2]  # skip every 2nd item: once per field
            if len(pulldown_cycle) <= 1:
                # no pulldown, or one strangler rff flag in the flags, only one rff index is useless
                pulldown_cycle = 0  # so just use 0 and assume its a mistake/mastering error
            else:
                # get the cycle by grouping every 2 flag indexes together, then subtracting the right-most (1) index
                # with the left-most (0) index and getting the most common number and adding 1 to it to be one-indexed.
                # Getting the common number is needed as interlaced sections in variable scan-type (VST) content
                # messes up the calculations where it enters and exits interlaced sections.
                # todo; that can be avoided by doing this check sectioned to each interlaced section and ignore the
                #       last subtraction. This would allow for Variable Pull Down computation, but from there a common
                #       check would still be necessary unless all of them from all sections match (which is likely).
                pulldown_cycle = list(zip(pulldown_cycle[::2], pulldown_cycle[1::2]))
                pulldown_cycle = [right - left for left, right in pulldown_cycle]
                pulldown_cycle = max(set(pulldown_cycle), key=pulldown_cycle.count) + 1  # +1 to one-index it

            coded_pictures = len(flags)
            progressive_pictures = sum(f["progressive_frame"] for f in flags)
            pulldown_count = int(sum(f["progressive_frame"] and f["rff"] for f in flags) / 2)  # / 2: once per field

            match_cycle, match_offsets = d2v_vst_vfr_mode

            if progressive_pictures == coded_pictures:
                # Mode 0: The FPS doesn't need matching, however it may be set wrong by d2vsource if the
                # video had any rff flags.
                if pulldown_cycle:
                    self.clip = core.std.AssumeFPS(
                        self.clip,
                        fpsnum=self.clip.fps.numerator - (self.clip.fps.numerator / pulldown_cycle),
                        fpsden=self.clip.fps.denominator
                    )
            elif not match_cycle:
                # Mode A (default): Match FPS by duplicating the progressive frames with RFF flags.
                progressive_rff_indexes = [n for n, f in enumerate(flags) if f["progressive_frame"] and f["rff"]]
                progressive_rff_indexes = progressive_rff_indexes[::2]  # skip every 2nd item: once per field
                if progressive_rff_indexes:
                    self.clip = core.std.DuplicateFrames(clip=self.clip, frames=progressive_rff_indexes)
                    flags = [(
                        [f, dict(**{**f, **{"progressive_frame": True, "rff": False, "tff": False}})]
                        if i in progressive_rff_indexes else [f]
                    ) for i, f in enumerate(flags)]
                    flags = list(itertools.chain.from_iterable(flags))
            else:
                # Mode B: Match FPS by decimating only the interlaced sections (prior to deinterlacing).
                # WARNING! This CAN cause problems. If the video has burned-in interlacing and therefore
                # butchered RFF flags on them (or rather not on them) can cause those sections to play out
                # longer than they should frame duration wise. Resulting in a de-sync. Only use this mode on
                # properly mastered and clean VST discs.
                if match_cycle is True:
                    match_cycle = pulldown_cycle  # True as cycle is a "symbol" for using pulldown_cycle
                if not isinstance(match_offsets, list) or not match_offsets:
                    # offsets array that removes the last frame of the cycle
                    match_offsets = list(range(match_cycle - 1))
                if len(match_offsets) < 1 or len(match_offsets) > match_cycle:
                    raise ValueError("The length of offsets provided cannot be less than 1 or more than the cycle")

                progressive_frames = group_by_int([n for n, f in enumerate(flags) if f["progressive_frame"]])
                interlaced_frames = group_by_int([n for n, f in enumerate(flags) if not f["progressive_frame"]])

                wanted_fps_num = self.clip.fps.numerator - (self.clip.fps.numerator / match_cycle)

                self.clip = core.std.Splice([x for _, x in sorted(
                    [
                        # progressive sections:
                        (
                            x[0],  # first frame # of the section, used for sorting when splicing
                            core.std.AssumeFPS(
                                self.clip[x[0]:x[-1] + 1],
                                fpsnum=wanted_fps_num,
                                fpsden=self.clip.fps.denominator
                            )
                        ) for x in progressive_frames
                    ] + [
                        # interlaced sections:
                        (
                            x[0],
                            core.std.SelectEvery(
                                self.clip[x[0]:x[-1] + 1],
                                match_cycle,
                                match_offsets
                            )
                        ) for x in interlaced_frames
                    ],
                    key=lambda section: int(section[0])
                )])

                interlaced_frames = [
                    n
                    for s in interlaced_frames
                    for n in list_select_every(s, match_cycle, match_offsets, inverse=True)
                ]
                flags = [f for f in flags if f["index"] not in interlaced_frames]

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
                if isinstance(dar, list):
                    dar = dar[0]
                par = calculate_par(self.clip.width, self.clip.height, *[int(x) for x in dar.split(":")])
                sar = calculate_aspect_ratio(self.clip.width, self.clip.height)
                self.clip = core.text.Text(
                    self.clip,
                    " " + (" \n ".join([
                        os.path.basename(self.file_path),
                        "Loaded with %s" % self.sourcer,
                        "- {:,d} coded pictures, which {:.2f}% of are Progressive".format(
                            coded_pictures, (progressive_pictures / coded_pictures) * 100
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
