# std vs
from vapoursynth import core
import vapoursynth as vs
# pvsfunc
from pvsfunc.helpers import anti_file_prefix, get_mime_type, get_video_codec, get_d2v


CODEC_SOURCER_MAP = {
    "V_MPEG1": "core.d2v.Source",
    "V_MPEG2": "core.d2v.Source",
    # codecs not listed here will default to `core.ffms2.Source`
}

SOURCER_ARGS_MAP = {
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

    def __init__(self, file_path):
        self.clip = None
        self.file_path = anti_file_prefix(file_path)
        self.file_type = get_mime_type(self.file_path)
        self.video_codec = get_video_codec(self.file_path)
        self.sourcer = self.get_sourcer(self.video_codec)
        # sourcer preparations
        if self.sourcer == "core.d2v.Source":
            # make sure a d2v file for this video exists
            self.file_path = get_d2v(self.file_path)
        # load video to clip using sourcer
        self.clip = eval(self.sourcer)(self.file_path, **SOURCER_ARGS_MAP[self.sourcer])
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
