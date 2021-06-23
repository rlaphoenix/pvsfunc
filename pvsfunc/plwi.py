import functools
import subprocess
from pathlib import Path

import vapoursynth as vs
from pymediainfo import MediaInfo
from vapoursynth import core

from pvsfunc.helpers import calculate_aspect_ratio, get_standard


class PLWI:
    """
    Apply operations related to L-SMASH-Works and it's indexer file format lwi.

    <!> Currently very basic, essentially only a loader with a basic deinterlacer.
        Once a parser for .lwi indexes is set-up, a lot more will be possible.
    """

    def __init__(self, file: str, verbose=False):
        """Load a file using core.lsmas.LWLibavSource, prepare source for optimal use."""
        if not hasattr(core, "lsmas"):
            raise RuntimeError(
                "Required plugin lsmas for namespace 'lsmas' not found. "
                "See https://github.com/VFR-maniac/L-SMASH-Works"
            )
        self.file = self._fps_reset(Path(file))  # destroy container-set FPS (causes problems)
        self.clip = core.lsmas.LWLibavSource(
            self.file,
            stream_index=-1,  # get best stream in terms of res
            dr=False  # enabling this seemed to cause issues on Linux for me
        )

        if verbose:
            standard = get_standard(self.clip.fps.numerator / self.clip.fps.denominator)
            sar = calculate_aspect_ratio(self.clip.width, self.clip.height)
            self.clip = core.text.Text(
                self.clip,
                text=f" {standard}  SAR: {sar} ",
                alignment=1,
                scale=1
            )

    def deinterlace(self, kernel: functools.partial, verbose=False):
        """
        Deinterlace clip using specified kernel in an optimal way.

        It only deinterlaces frames marked as interlaced by the sourcer. However, this isn't as good as the
        PD2V method, as it doesn't take into account the .lwi frame indexed data.
        Instead it assumes LWLibavSource has done it correctly, and assumes it did it at all.

        Kernel:
        - Should be a callable function, with the first argument being the clip.
        - The function needs an argument named `TFF` or `tff` for specifying field order.
        - You can use functools.partial to specify arguments to the kernel to be used.
        - Field order should never be specified manually, unless you really really need to.

        <!> If the source is VFR, it's currently recommended to use something else entirely as this
                class does not yet support frame matching.
        """
        if not isinstance(self.clip, vs.VideoNode):
            raise TypeError("This is not a clip")
        if not callable(kernel):
            raise ValueError("Invalid kernel, must be a callable")
        if len(kernel.args) > 1:
            raise ValueError("Invalid kernel, no positional arguments should be used")

        if kernel.keywords.get("FPSDivisor", 2) != 2:
            # TODO: add support for variable FPS Divisors
            raise ValueError("LWLibavSource only supports QTGMC single-rate output (FPSDivisor=2)")

        deinterlaced_tff = kernel(self.clip, TFF=True)
        deinterlaced_bff = kernel(self.clip, TFF=False)

        def _d(n: int, f: vs.VideoFrame, c: vs.VideoNode, tff: vs.VideoNode, bff: vs.VideoNode):
            # deinterlace if _FieldBased > 0
            rc = {0: c, 1: bff, 2: tff}[f.props["_FieldBased"]]  # type: ignore
            return core.text.Text(
                rc,
                {0: "Progressive", 1: "Deinterlaced (BFF)", 2: "Deinterlaced (TFF)"}[f.props["_FieldBased"]],
                alignment=3
            ) if verbose else rc

        self.clip = core.std.FrameEval(
            self.clip,
            functools.partial(
                _d,
                c=self.clip,
                tff=deinterlaced_tff,
                bff=deinterlaced_bff
            ),
            prop_src=self.clip
        )
        return self

    @staticmethod
    def _fps_reset(file_path: Path) -> Path:
        """Remove container-set FPS to only have the encoded FPS."""
        video_tracks = [x for x in MediaInfo.parse(file_path).tracks if x.track_type == "Video"]
        if not video_tracks:
            raise Exception("File does not have a video track, removing container-set FPS isn't possible.")
        video_track = video_tracks[0]
        if video_track.original_frame_rate is None:
            # no container-set FPS to remove, return unchanged
            return file_path
        out_path = file_path.with_suffix(".pfpsreset.mkv")
        if out_path.is_file():
            # an fps reset was already run on this file, re-use
            # TODO: could be untrusted, user might just make a file named this
            return out_path
        if video_track.framerate_original_num and video_track.framerate_original_den:
            original_fps = "%s/%s" % (video_track.framerate_original_num, video_track.framerate_original_den)
        else:
            original_fps = video_track.original_frame_rate
        subprocess.check_output([
            "mkvmerge", "--output", out_path,
            "--default-duration", "%d:%sfps" % (video_track.track_id - 1, original_fps),
            file_path
        ], cwd=file_path.parent)
        return out_path
