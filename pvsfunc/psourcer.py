import mimetypes
from typing import Union

import vapoursynth as vs
from vapoursynth import core

from pvsfunc.helpers import anti_file_prefix, get_video_codec, fps_reset

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
    "core.lsmas.LWLibavSource": {
        "stream_index": -1,  # get best stream in terms of res
        "dr": False  # enabling this seemed to cause issues on Linux for me
    }
}


class PSourcer:
    """
    PSourcer (PHOENiX Sourcer).

    <!> Deprecation notice. This class is being phased out and will be removed entirely soon.
        Use PD2V for MPEG-1/MPEG-2, and for other codecs and formats, more classes will be made
        before PSourcer is removed.

    Loads an input file path with the most optimal clip source based on the file.
    This is mainly a wrapper function for my other classes and functions of pvsfunc.
    The sourcer (and it's arguments) are based on my own personal opinions.

    core.imwri.Read is used on images, core.lsmas.LWLibavSource is used on everything else.
    Again, it's important that you use PD2V and not PSourcer for MPEG-1/MPEG-2 videos!!
    """

    def __init__(self, file_path, debug=False):
        """
        Load an input file path with the most optimal clip source based on the file.
        For example an MPEG-4/AVC/H.264 video will load using core.lsmas.LWLibavSource.

        :param file_path: Input file path, can be any extension and can include `file://` prefix.
        :param debug: Print various information and metadata about the loaded clip.
        """
        self.file_path = anti_file_prefix(file_path)
        self.debug = debug
        self.clip = None

        self.file_type = mimetypes.guess_type(self.file_path)[0] or "video"  # fallback to video type
        self.file_type = self.file_type.split("/")[0]
        if self.file_type not in ("video", "image"):
            raise ValueError("Only Video or Image files are supported. (%s)" % self.file_type)
        self.video_codec = get_video_codec(self.file_path)

        if self.video_codec == -1:
            raise ValueError("File path supplied does not exist")
        if self.video_codec == -2:
            raise ValueError("File supplied does not have a Video or Image track")
        if self.file_type == "image":
            # we do this after get_video_codec so it checks if an image
            # track actually exists, and not just an empty image container
            self.video_codec = "IMAGE"

        self.sourcer = CODEC_SOURCER_MAP.get(self.video_codec, "core.lsmas.LWLibavSource")
        if self.sourcer == "core.d2v.Source":
            raise Exception("For MPEG-1/MPEG-2 videos, use P2V instead of PSourcer.")
        elif self.sourcer == "core.lsmas.LWLibavSource":
            if not hasattr(core, "lsmas"):
                raise RuntimeError(
                    "Required plugin lsmas for namespace 'lsmas' not found. "
                    "https://github.com/VFR-maniac/L-SMASH-Works"
                )
            self.file_path = fps_reset(self.file_path)  # destroy container-set FPS

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
