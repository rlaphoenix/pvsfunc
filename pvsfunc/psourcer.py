# std vs
from vapoursynth import core
import vapoursynth as vs
# std
import os
import glob
import shutil
import subprocess
import mimetypes
# pip packages
from pymediainfo import MediaInfo


class PSourcer:
    """
    PSourcer (PHOENiX Sourcer)
    Loads an input file path with the most optimal clip source based on the file.
    This is mainly a wrapper function for my other classes and functions of pvsfunc.
    The sourcers and settings they source with are based on my own personal opinions.
    """

    CODEC_SOURCER_MAP = {
        "V_MPEG1": "core.d2v.Source",
        "MPEG-1 Video": "core.d2v.Source",
        "V_MPEG2": "core.d2v.Source",
        "MPEG-2 Video": "core.d2v.Source",
        # codecs not listed here will default to `core.ffms2.Source`
    }

    SOURCER_FUNC_MAP = {
        "core.d2v.Source": core.d2v.Source,
        "core.ffms2.Source": core.ffms2.Source
    }

    SOURCER_ARGS_MAP = {
        "core.d2v.Source": {
            # ignore rff (pulldown flags) as we do not want it to interlace
            # the pulldown frames and end up giving us more work...
            "rff": False
        },
        "core.ffms2.Source": {
            # disable the alpha channel as it often causes an incompatability
            # with some functions due to the extra channel
            "alpha": False
        }
    }

    def __init__(self, file_path):
        self.clip = None
        self.file_path = self.anti_file_prefix(file_path)
        self.file_type = self.get_file_type(self.file_path)
        self.video_codec = self.get_video_codec(self.file_path)
        self.sourcer = self.get_sourcer(self.video_codec)
        # sourcer preparations
        if self.sourcer == "core.d2v.Source":
            # make sure a d2v file for this video exists
            self.file_path = self.get_d2v(self.file_path)
        # load video to clip using sourcer
        #self.clip = self.SOURCER_FUNC_MAP[self.sourcer](self.file_path, **self.SOURCER_ARGS_MAP[self.sourcer])
        self.clip = core.d2v.Source(self.file_path, **self.SOURCER_ARGS_MAP[self.sourcer])
        # set various props that the user may find helpful
        for k, v in [
            ("FilePath", self.file_path),
            ("Codec", self.video_codec),
            ("Sourcer", str(self.sourcer))
        ]:
            # why the fuck is there no SetFrameProps, cmon...
            self.clip = core.std.SetFrameProp(self.clip, prop=f"PVS{k}", data=v)
    
    def anti_file_prefix(self, path):
        """Remove prefixed 'file://' from path"""
        if path.lower().startswith("file://"):
            path = path[7:]
            if os.name == "nt":
                # windows sometimes adds an extra leading /
                path = path.lstrip("/")
        return path
    
    def get_file_type(self, file_path):
        """Get file mimetype based on file contents or extension"""
        # initialise mimetypes, let it load all mimes
        mimetypes.init()
        # get the file extension
        file_ext = os.path.splitext(file_path)[-1]
        # check if the file is a D2V/DGIndexProjectFile
        with open(file_path, mode="rb") as f:
            if f.read(18) == "DGIndexProjectFile".encode("utf-8"):
                if f.read(2) != bytes([0x31, 0x36]):
                    raise ValueError(
                        "pvsfunc.PSourcer: D2V was created with an unsupported indexer, please use DGIndex v1.5.8." +
                        (" It works perfectly fine under Wine." if os.name != "nt" else "")
                    )
                return "video/d2v"
        # check if the file extension is recognized
        if file_ext not in mimetypes.types_map:
            raise ValueError(f"pvsfunc.PSourcer: Unrecognised file extension ({file_ext})")
        # ensure that the mime is a video file
        if not mimetypes.types_map[file_ext].startswith("video/"):
            raise ValueError(f"pvsfunc.PSourcer: Non-video file type ({mimetypes.types_map[file_ext]})")
        # return the mime
        return mimetypes.types_map[file_ext]
    
    def get_video_codec(self, file_path):
        """Get video codec using MediaInfo"""
        video_track = [t for t in MediaInfo.parse(
            filename=file_path
        ).tracks if t.track_type == "Video"]
        if not video_track:
            raise ValueError("No video track in file...")
        video_track = video_track[0]
        # we try both as in some cases codec_id isn't set
        return video_track.codec_id or video_track.commercial_name
    
    def get_sourcer(self, video_codec):
        """Get clip sourcer function based on video codec"""
        if video_codec not in self.CODEC_SOURCER_MAP:
            # default to FFMPEG-based sourcer for wide compatability
            return "core.ffms2.Source"
        return self.CODEC_SOURCER_MAP[video_codec]
    
    def get_d2v(self, file_path):
        """Demux video track and generate a D2V file for it if needed"""
        # create file_path locateion of the d2v path
        d2v_path = f"{os.path.splitext(file_path)[0]}.d2v"
        if os.path.exists(d2v_path):
            print("Skipping generation as a D2V file already exists")
            return d2v_path
        # demux the mpeg stream
        mpg_path = f"{os.path.splitext(file_path)[0]}.mpg"
        if os.path.exists(mpg_path):
            print("Skipping demuxing of raw mpeg stream as it already exists")
        else:
            mkvextract_path = shutil.which("mkvextract")
            if not mkvextract_path:
                raise RuntimeError(
                    "pvsfunc.PSourcer: Required binary 'mkvextract' not found. "
                    "Install MKVToolNix and make sure it's binaries are in the environment path."
                )
            subprocess.run([
                mkvextract_path, os.path.basename(file_path),
                # todo ; this assumes the track with track-id of 0 is the video, not ideal
                "tracks", f"0:{os.path.basename(mpg_path)}"
            ], cwd=os.path.dirname(file_path))
        # use dgindex to create a d2v file for the demuxed track
        dgindex_path = shutil.which("DGIndex.exe") or shutil.which("dgindex.exe")
        if not dgindex_path:
            raise RuntimeError(
                "pvsfunc.PSourcer: This video file will need a required binary 'DGIndex.exe' which isn't found.\n"
                "tl-dr; add DGIndex.exe to your systems environment path. Name it exactly `DGIndex.exe`.\n"
                "Windows: Download DGIndex and place the files into 'C:/Program Files (x86)/DGIndex' (manually create folder). "
                "Once done, add that path to System Environment Variables, run a google search for instructions.\n"
                "Linux: Lmao im pretty sure your capable of figuring it out."
            )
        subprocess.run([
            dgindex_path,
            "-i", os.path.basename(mpg_path),
            "-ia", "5",  # iDCT Algorithm, 5=IEEE-1180 Reference
            "-fo", "2",  # Field Operation, 2=Ignore Pulldown Flags
            "-yr", "1",  # YUV->RGB, 1=PC Scale
            "-om", "0",  # Output Method, 0=None (just d2v)
            "-hide", "-exit",  # start hidden and exit when saved
            "-o", os.path.splitext(os.path.basename(file_path))[0]
        ], cwd=os.path.dirname(file_path))
        # return file path of the new d2v file
        return d2v_path
