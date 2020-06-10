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
    # check for special file types if theres no mime type
    if file_ext not in mimetypes.types_map:
        # check if the file is a D2V/DGIndexProjectFile
        with open(file_path, mode="rb") as f:
            if f.read(18) == "DGIndexProjectFile".encode("utf-8"):
                if f.read(2) != bytes([0x31, 0x36]):
                    raise ValueError(
                        "pvsfunc.get_file_type: D2V was created with an unsupported indexer, please use DGIndex v1.5.8." +
                        (" It works perfectly fine under Wine." if os.name != "nt" else "")
                    )
                return "video/d2v"
        if file_ext.lower() == ".vob":
            return "video/vob"
        raise ValueError(f"pvsfunc.get_file_type: Unrecognised file extension ({file_ext})")
    mime_type = mimetypes.types_map[file_ext] if file_ext in mimetypes.types_map else None
    # ensure that the mime is a video or image file
    if not mime_type.startswith("video/") and not mime_type.startswith("image/"):
        raise ValueError(f"pvsfunc.get_file_type: Only Video or Image files are supported. ({mime_type})")
    # return the mime
    return mime_type


def get_video_codec(file_path: str) -> str:
    """Get video codec using MediaInfo"""
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return "?"
    track = [t for t in MediaInfo.parse(
        filename=file_path
    ).tracks if t.track_type in ["Video", "Image"]]
    if not track:
        raise ValueError("No video/image track in file...")
    track = track[0]
    # we try both as in some cases codec_id isn't set
    codec = track.codec_id or track.commercial_name
    # do some squashing to reduce amount of code repetition
    if codec == "MPEG-1 Video":
        return "V_MPEG1"
    if codec == "MPEG-2 Video":
        return "V_MPEG2"
    return codec


def get_d2v(file_path: str) -> str:
    """Demux video track and generate a D2V file for it if needed"""
    IS_VOB = os.path.splitext(file_path)[-1].lower() == ".vob"
    # create file_path location of the d2v path
    d2v_path = f"{os.path.splitext(file_path)[0]}.d2v"
    if os.path.exists(d2v_path):
        print("Skipping generation as a D2V file already exists")
        return d2v_path
    # demux the mpeg stream if needed
    vid_path = file_path
    if not IS_VOB:
        if os.path.splitext(file_path)[-1].lower() != ".mpeg":
            vid_path = f"{os.path.splitext(file_path)[0]}.mpg"
        if os.path.exists(vid_path):
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
                "tracks", f"0:{os.path.basename(vid_path)}"
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
        "-ai" if IS_VOB else "-i", os.path.basename(vid_path),
        "-ia", "5",  # iDCT Algorithm, 5=IEEE-1180 Reference
        "-fo", "2",  # Field Operation, 2=Ignore Pulldown Flags
        "-yr", "1",  # YUV->RGB, 1=PC Scale
        "-om", "0",  # Output Method, 0=None (just d2v)
        "-hide", "-exit",  # start hidden and exit when saved
        "-o", os.path.splitext(os.path.basename(file_path))[0]
    ], cwd=os.path.dirname(file_path))
    # return file path of the new d2v file
    return d2v_path

def gcd(a, b):
    """The GCD (greatest common divisor) is the highest number that evenly divides both width and height."""
    return a if b == 0 else gcd(b, a % b)

def calculate_aspect_ratio(width: int, height: int) -> str:
    """Calculate the aspect-ratio gcd string from resolution"""
    r = gcd(width, height)
    return f"{int(width / r)}:{int(height / r)}"

def calculate_par(width: int, height: int, aspect_ratio_w: int, aspect_ratio_h: int) -> str:
    """Calculate the pixel-aspect-ratio string from resolution"""
    par_w = height * aspect_ratio_w
    par_h = width * aspect_ratio_h
    par_gcd = gcd(par_w, par_h)
    par_w = int(par_w / par_gcd)
    par_h = int(par_h / par_gcd)
    return f"{par_w}:{par_h}"
