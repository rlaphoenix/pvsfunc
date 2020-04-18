# std
import os
import subprocess
import shutil
import mimetypes
# pip packages
from pymediainfo import MediaInfo


def anti_file_prefix(path: str) -> str:
    """Remove prefixed 'file://' from path"""
    if path.lower().startswith("file://"):
        path = path[7:]
        if os.name == "nt":
            # windows sometimes adds an extra leading /
            path = path.lstrip("/")
    return path


def get_mime_type(file_path: str) -> str:
    """Get file mime-type based on file contents or extension"""
    # initialise mime-types, let it load all mimes
    mimetypes.init()
    # get the file extension
    file_ext = os.path.splitext(file_path)[-1]
    # check if the file is a D2V/DGIndexProjectFile
    with open(file_path, mode="rb") as f:
        if f.read(18) == "DGIndexProjectFile".encode("utf-8"):
            if f.read(2) != bytes([0x31, 0x36]):
                raise ValueError(
                    "pvsfunc.get_file_type: D2V was created with an unsupported indexer, please use DGIndex v1.5.8." +
                    (" It works perfectly fine under Wine." if os.name != "nt" else "")
                )
            return "video/d2v"
    # check if the file extension is recognized
    if file_ext not in mimetypes.types_map:
        raise ValueError(f"pvsfunc.get_file_type: Unrecognised file extension ({file_ext})")
    # ensure that the mime is a video file
    if not mimetypes.types_map[file_ext].startswith("video/"):
        raise ValueError(f"pvsfunc.get_file_type: Non-video file type ({mimetypes.types_map[file_ext]})")
    # return the mime
    return mimetypes.types_map[file_ext]


def get_video_codec(file_path: str) -> str:
    """Get video codec using MediaInfo"""
    video_track = [t for t in MediaInfo.parse(
        filename=file_path
    ).tracks if t.track_type == "Video"]
    if not video_track:
        raise ValueError("No video track in file...")
    video_track = video_track[0]
    # we try both as in some cases codec_id isn't set
    codec = video_track.codec_id or video_track.commercial_name
    # do some squashing to reduce amount of code repetition
    if codec == "MPEG-1 Video":
        return "V_MPEG1"
    if codec == "MPEG-2 Video":
        return "V_MPEG2"
    return codec


def get_d2v(file_path: str) -> str:
    """Demux video track and generate a D2V file for it if needed"""
    # create file_path location of the d2v path
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
            "tl-dr; add DGIndex.exe to your system path. Ensure the executable is named exactly `DGIndex.exe`.\n"
            "Windows: Start Menu -> Environment Variables, Add DGIndex's folder to `PATH` variable.\n"
            "Linux: append to $PATH in /etc/profile, I recommend using `nano /etc/profile.d/env.sh`. Must reboot."
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


def calculate_aspect_ratio(width: int, height: int) -> str:
    """Calculate the aspect-ratio gcd string from resolution"""
    def gcd(a, b):
        """The GCD (greatest common divisor) is the highest number that evenly divides both width and height."""
        return a if b == 0 else gcd(b, a % b)
    r = gcd(width, height)
    return f"{int(width / r)}:{int(height / r)}"
