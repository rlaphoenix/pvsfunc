import os
import shutil
import subprocess
from typing import Union

from pymediainfo import MediaInfo


def anti_file_prefix(path: str) -> str:
    """Remove prefixed 'file://' from path."""
    if path.lower().startswith("file://"):
        path = path[7:]
        if os.name == "nt":
            # windows sometimes adds an extra leading /
            path = path.lstrip("/")
    return path


def get_video_codec(file_path: str) -> Union[str, int]:
    """
    Get video codec using MediaInfo.
    :param file_path: Path to a video or image file
    :returns: -1 if file does not exist,
              -2 if no Video or Image track in the file exists
              or finally a unique codec ID str
    """
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return -1
    track = [t for t in MediaInfo.parse(
        filename=file_path
    ).tracks if t.track_type in ["Video", "Image"]]
    if not track:
        return -2
    track = track[0]
    # we try both as in some cases codec_id isn't set
    codec = track.codec_id or track.commercial_name
    # do some squashing to reduce amount of code repetition
    return {
        "MPEG-1 Video": "V_MPEG1",
        "MPEG-2 Video": "V_MPEG2"
    }.get(codec, codec)


def get_d2v(file_path: str) -> str:
    """Demux video track and generate a D2V file for it if needed."""
    is_vob = os.path.splitext(file_path)[-1].lower() == ".vob"
    d2v_path = os.path.splitext(file_path)[0] + ".d2v"
    if os.path.exists(d2v_path):
        print("Skipping generation as a D2V file already exists")
        return d2v_path
    # demux the mpeg stream if not a .VOB or .MPEG file
    demuxed_ext = [".mpeg", ".mpg", ".m2v", ".vob"]
    vid_path = file_path
    if os.path.splitext(file_path)[-1].lower() in demuxed_ext:
        print("Skipping demuxing of raw MPEG stream as it already exists or is unnecessary")
    else:
        vid_path = None
        for ext in demuxed_ext:
            x = os.path.splitext(file_path)[0] + ext
            if os.path.exists(x) and os.path.isfile(x):
                vid_path = x
                break
        if not vid_path:
            vid_path = os.path.splitext(file_path)[0] + demuxed_ext[0]
            mkvextract_path = shutil.which("mkvextract")
            if not mkvextract_path:
                raise RuntimeError(
                    "pvsfunc.PSourcer: Executable 'mkvextract' not found, but is needed for the provided file.\n"
                    "Install MKVToolNix and make sure it's binaries are in the environment path."
                )
            subprocess.run([
                mkvextract_path, os.path.basename(file_path),
                # todo ; this assumes the track with track-id of 0 is the video, not ideal
                "tracks", "0:" + os.path.basename(vid_path)
            ], cwd=os.path.dirname(file_path), check=True)
    # use dgindex to create a d2v file for the demuxed track
    dgindex_path = shutil.which("DGIndex.exe") or shutil.which("dgindex.exe")
    if not dgindex_path:
        raise RuntimeError(
            "pvsfunc.PSourcer: Executable 'DGIndex.exe' not found, but is needed for the provided file.\n"
            "Add DGIndex.exe to your system path. Ensure the executable is named exactly `DGIndex.exe`.\n"
            "Windows: Search Start Menu for 'Environment Variables', Add DGIndex's folder to the `PATH` variable.\n"
            "Linux: Append to $PATH in /etc/profile.d, I recommend using `nano /etc/profile.d/env.sh`. Must reboot. " +
            "Make sure DGIndex.exe is marked as executable (chmod +x)."
        )
    args = []
    if dgindex_path.startswith("/"):
        # required to do it this way for whatever reason. Directly calling it sometimes fails.
        args.extend(["wine", "start", "/wait", "Z:" + dgindex_path])
    else:
        args.extend([dgindex_path])
    args.extend([
        # all the following D2V settings are VERY important
        # please do not change these unless there's a good verifiable reason
        "-ai" if is_vob else "-i", os.path.basename(vid_path),
        "-ia", "5",  # iDCT Algorithm, 5=IEEE-1180 Reference
        "-fo", "2",  # Field Operation, 2=Ignore Pulldown Flags
        "-yr", "1",  # YUV->RGB, 1=PC Scale
        "-om", "0",  # Output Method, 0=None (just d2v)
        "-hide", "-exit",  # start hidden and exit when saved
        "-o", os.path.splitext(os.path.basename(file_path))[0]
    ])
    subprocess.run(args, cwd=os.path.dirname(file_path), check=True)
    # Replace the Z:\bla\bla paths to /bla/bla unix paths, if on a unix system.
    # This is needed simply due to how d2vsource loads the video files. On linux it doesn't use wine,
    # so Z:\ paths obviously won't exist.
    if dgindex_path.startswith("/"):
        with open(d2v_path, "rt", encoding="utf-8") as f:
            d2v_content = f.read().splitlines()
        d2v_content = [(x[2:].replace("\\", "/") if x.startswith("Z:\\") else x) for x in d2v_content]
        with open(d2v_path, "wt", encoding="utf-8") as f:
            f.write("\n".join(d2v_content))
    # return file path of the new d2v file
    return d2v_path


def fps_reset(file_path: str) -> str:
    """Remove container-set FPS to only have the encoded FPS."""
    video_tracks = [x for x in MediaInfo.parse(file_path).tracks if x.track_type == "Video"]
    if not video_tracks:
        raise Exception("File does not have a video track, removing container-set FPS isn't possible.")
    video_track = video_tracks[0]
    if video_track.original_frame_rate is None:
        # no container-set FPS to remove, return unchanged
        return file_path
    out_path = file_path + ".pfpsreset.mkv"
    if os.path.exists(out_path):
        # an fps reset was already run on this file, re-use
        # todo ; could be dangerous, user might just make a file named this :/
        return out_path
    if video_track.framerate_original_num and video_track.framerate_original_den:
        original_fps = "%s/%s" % (video_track.framerate_original_num, video_track.framerate_original_den)
    else:
        original_fps = video_track.original_frame_rate
    subprocess.check_output([
        "mkvmerge", "--output", out_path,
        "--default-duration", "%d:%sfps" % (video_track.track_id - 1, original_fps),
        file_path
    ], cwd=os.path.dirname(file_path))
    return out_path


def gcd(a, b):
    """Calculate the GCD (greatest common divisor); the highest number that evenly divides both width and height."""
    return a if b == 0 else gcd(b, a % b)


def calculate_aspect_ratio(width: int, height: int) -> str:
    """Calculate the aspect-ratio gcd string from resolution."""
    r = gcd(width, height)
    return "%d:%d" % (int(width / r), int(height / r))


def calculate_par(width: int, height: int, aspect_ratio_w: int, aspect_ratio_h: int) -> str:
    """Calculate the pixel-aspect-ratio string from resolution."""
    par_w = height * aspect_ratio_w
    par_h = width * aspect_ratio_h
    par_gcd = gcd(par_w, par_h)
    par_w = int(par_w / par_gcd)
    par_h = int(par_h / par_gcd)
    return "%d:%d" % (par_w, par_h)
