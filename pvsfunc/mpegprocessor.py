# std vs
from vapoursynth import core  # this may give a linter error, ignore
# std py
import os
import functools
import subprocess
# vs func repos
import havsfunc
# pip packages
from pymediainfo import MediaInfo
from pyd2v import D2V


class MpegProcessor:
    def __init__(self, file_path, source_cfg=None, dgindex_path="DGIndex.exe", debug=False):
        """
        MpegProcessor is a convenience wrapper for loading and using MPEG videos.
        It's primary function is to handle the loading and handle video fields to
        return a CFR (Constant frame-rate) progressive video.
        :param file_path: Path to a file to import. An MKV file is recommended no
        matter what the video codec is.
        :param source_cfg: A dictionary of key=value pairs that will be unpacked and
        provided to whatever clip Sourcing function get's used e.g.
        {"core.d2v.Source": { "rff": True }, "core.ffms2.Source": { "alpha": False }}
        :param dgindex_path: A file path to DGIndex. On Windows if the exe is in your
        Environment Path, you may simply put "DGIndex" or "DGIndex.exe".
        :param debug: Debug Mode, Enable it if you want to debug frame information.
        """
        # exports handy to parent
        self.clip = None
        self.clip_cfg = None
        self.clip_src = None
        self.fileid = None
        self.mediainfo = None
        self.standard = None
        # internal variables
        self.debug = debug
        self.file_path = file_path
        self.file_ext = os.path.splitext(self.file_path)[-1].lower()[1:]
        self.file_internal = None
        self.dgindex_path = dgindex_path
        # get internal file paths if exist
        if self.file_ext == "d2v":  # DGIndex Project Files
            self.file_internal = D2V(self.file_path).videos[0]
            if self.file_internal and not os.path.isabs(self.file_internal):
                # convert relative to absolute
                self.file_internal = os.path.join(os.path.dirname(self.file_path), self.file_internal)
        # load mediainfo from MediaInfo
        self.mediainfo = [t for t in MediaInfo.parse(
            filename=self.file_internal or self.file_path
        ).tracks if t.track_type == "Video"][0]
        # prepare a unique ID for input
        self.fileid = self.mediainfo.codec_id or self.mediainfo.commercial_name
        if self.fileid == "MPEG-2 Video":
            self.fileid = "V_MPEG2"
        elif self.fileid == "MPEG-1 Video":
            self.fileid = "V_MPEG1"
        # load file into clip with a Sourcer
        if self.fileid == "V_MPEG2":
            # core.d2v.Source is the only source available for frame-accuracy
            d2v_path = self.file_path
            if self.file_ext != "d2v":
                # if the file path isn't a d2v, force it to be
                d2v_path = f"{os.path.splitext(d2v_path)[0]}.d2v"
                if not os.path.exists(d2v_path):
                    # couldn't find d2v, generate one on-the-fly
                    mpg_path = f"{os.path.splitext(d2v_path)[0]}.mpg"
                    if not os.path.exists(mpg_path):
                        try:
                            # couldn't find mpg, generate one on-the-fly
                            subprocess.run([
                                "mkvextract", os.path.basename(self.file_path),
                                "tracks", f"0:{os.path.basename(mpg_path)}"
                            ], cwd=os.path.dirname(self.file_path))
                        except FileNotFoundError:
                            raise RuntimeError(
                                "MpegProcessor: Required binary 'mkvextract' not found. "
                                "Install MKVToolNix and make sure it's binaries are in the environment path."
                            )
                    try:
                        # generate d2v from mpg
                        subprocess.run([
                            self.dgindex_path,
                            "-i", os.path.basename(mpg_path),
                            "-ia", "5",  # iDCT Algorithm, 5=IEEE-1180 Reference
                            "-fo", "2",  # Field Operation, 2=Ignore Pulldown Flags
                            "-yr", "1",  # YUV->RGB, 1=PC Scale
                            "-om", "0",  # Output Method, 0=None (just d2v)
                            "-hide", "-exit",  # start hidden and exit when saved
                            "-o", os.path.splitext(os.path.basename(d2v_path))[0]
                        ], cwd=os.path.dirname(d2v_path))
                    except FileNotFoundError:
                        raise RuntimeError(
                            "MpegProcessor: Required binary 'DGIndex' not found.\n"
                            "Windows: Download DGIndex and place the folder into 'C:/Program Files (x86)/DGIndex' (manually create folder). "
                            "Once done, add that path to System Environment Variables, run a google search for instructions.\n"
                            "Linux: Put the path to DGIndex.exe in the dgindex_path argument. Python Subprocess doesnt follow bash's PATH or alias, "
                            "so specifying path manually will have to be done."
                        )
                    # make sure d2v's internal mpg file path is absolute path to mpg
                    with open(d2v_path, mode="r") as f:
                        _D2V = f.read().splitlines()
                    _D2V[2] = os.path.join(os.path.dirname(d2v_path), os.path.basename(mpg_path))
                    with open(d2v_path, mode="w") as f:
                        f.write("\n".join(_D2V))
            self.clip_cfg = {
                **(source_cfg["core.d2v.Source"] if source_cfg and "core.d2v.Source" in source_cfg else {}),
                "input": d2v_path
            }
            self.clip_src = "d2v"
            self.clip = core.d2v.Source(**self.clip_cfg)
            if "rff" in self.clip_cfg and not self.clip_cfg["rff"]:
                d2v = D2V(d2v_path)
                if d2v.data_type == "100.00% FILM":
                    # fix rff=False's returned FPS for FILM content
                    self.clip = core.std.AssumeFPS(self.clip, fpsnum=24000, fpsden=1001)
        elif self.fileid in ["V_MPEG1", "V_MPEG4/ISO/AVC"]:
            self.clip_cfg = {
                **(source_cfg["core.ffms2.Source"] if source_cfg and "core.ffms2.Source" in source_cfg else {}),
                "source": self.file_path,
                "alpha": False
            }
            self.clip_src = "ffms2"
            self.clip = core.ffms2.Source(**self.clip_cfg)
        else:
            raise ValueError(f"MpegProcessor: Video Codec ({self.fileid}) not currently supported")
        # detect standard
        if self.clip.fps.numerator == 25 and self.clip.fps.denominator == 1:
            self.standard = "PAL"
        elif self.clip.fps.numerator == 30000 and self.clip.fps.denominator == 1001:
            self.standard = "NTSC"
        elif self.clip.fps.numerator == 24000 and self.clip.fps.denominator == 1001:
            self.standard = "NTSC-FILM"
        elif self.clip.fps.numerator == 24 and self.clip.fps.denominator == 1:
            self.standard = "FILM"
        else:
            self.standard = "UNKNOWN!"

    def deinterlace(self, vfm_cfg={}, qtgmc_cfg={}, tff=None):
        if tff is None:
            # try get tff from first first frame
            # todo ; try figure out a better way to get tff, as this may not be accurate
            first_frame = self.clip.get_frame(0).props
            if "_FieldBased" in first_frame:
                tff = first_frame["_FieldBased"] != 1  # if its 0=frame or 2=top, tff=True
        if "FPSDivisor" in qtgmc_cfg and qtgmc_cfg["FPSDivisor"] == 1:
            # we need a clip with double the frame rate and double frame length to hold qtgmc's Double-rate frames
            format_clip = core.std.BlankClip(
                clip=self.clip,
                length=len(self.clip)*2,
                fpsnum=self.clip.fps.numerator*2,
                fpsden=self.clip.fps.denominator
            )
        else:
            format_clip = self.clip
        # prepare vfm
        vfm = core.vivtc.VFM(**{
            # defaults
            **{"order": 1 if tff else 0, "field": 2, "mode": 0},
            # user configuration
            **dict(vfm_cfg),
            # required
            **{"clip": self.clip}
        })
        # prepare qtgmc
        qtgmc = havsfunc.QTGMC(**{
            # defaults
            **{
                "FPSDivisor": 2,
                "Preset": "Placebo",
                "MatchPreset": "Placebo",
                "MatchPreset2": "Placebo",
                "TFF": tff,
                "InputType": 0,
                "SourceMatch": 3,
                "Lossless": 2,
                "Sharpness": 0.2,
                "ShutterBlur": 0,
                "ShutterAngleSrc": 0,
                "ShutterAngleOut": 0,
                "SBlurLimit": 0
            },
            # user configuration
            **dict(qtgmc_cfg),
            # required
            **{
                # If QTGMC will produce anything other than Single-rate frame rate (e.g. FPSDivisor=1)
                # then vfm will desync from QTGMC as vfm returns Single-rate frame rate. We use VFM's
                # clip otherwise to lower the amount of time's QTGMC needs to run as VFM will take care
                # of the frames/fields it can first.
                "Input": vfm if "FPSDivisor" not in qtgmc_cfg or qtgmc_cfg["FPSDivisor"] == 2 else self.clip
            }
        })
        # calculate when VFM/QTGMC is needed
        # todo ; On the FieldBased == 0 line inside the first functools.partial, if it returns it's else, then it gets very very slow due
        # to it using a all of the memory available in `cores` max memory cache pool. This is causing terrible slowdowns. It seems to be
        # related to QTGMC specifically as it only occurs if the else is returning `qtgmc` or the second FrameEval. No idea why this is
        # happening :(
        self.clip = core.std.FrameEval(
            format_clip,
            functools.partial(
                lambda n, f, og: (
                    core.text.Text(og, "Untouched Frame (_FieldBased=0)", alignment=1) if self.debug else og
                ) if f.props["_FieldBased"] == 0 and ("FPSDivisor" not in qtgmc_cfg or qtgmc_cfg["FPSDivisor"] == 2) else core.std.FrameEval(
                    # calculate whether to use qtgmc or vfm
                    format_clip,
                    functools.partial(
                        lambda n, f: (
                            core.text.Text(qtgmc, f"Deinterlaced Frame (via QTGMC) [tff={tff}]", alignment=1) if self.debug else qtgmc
                        ) if self.standard == "PAL" or ("FPSDivisor" in qtgmc_cfg and qtgmc_cfg["FPSDivisor"] != 2) or f.props["_Combed"] > 0 else (
                            core.text.Text(vfm, "Matched Frame (via VFM match)", alignment=1) if self.debug else vfm
                        )
                    ),
                    prop_src=vfm
                ),
                og=self.clip
            ),
            prop_src=self.clip
        )
