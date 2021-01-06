import functools
from typing import List

from vapoursynth import core


class PDecimate:
    """PDecimate (PHOENiX Decimate)."""

    def __init__(self, clip, cycle, offsets, per_vob_id=True, mode=0, debug=False):
        """
        Decimates (deletes) frames in a specified pattern using cycle and offsets.
        This will typically be used for Inverse-Telecine purposes.

        :param clip: VapourSynth Clip (VideoNode) to decimate
        :param cycle: Defines the amount of frames to calculate offsets on at a time.
        :param offsets: Mode 0's offsets are a zero-indexed list. This indicates which frames to KEEP from the cycle.
                        Set to `None` when using mode=1.
        :param per_vob_id: When Clip is a DVD-Video Object (.VOB): Reset the cycle every time the VOB Cell changes.
        :param mode: 0=core.std.SelectEvery (recommended), 1=core.vivtc.VDecimate (be warned; its inaccurate!)
        :param debug: Skip decimation and print debugging information. Useful to check if the frames that the cycle
        and offset settings you have provided are correct and actually decimate the right frames.
        """
        self.clip = clip
        self.cycle = cycle
        self.offsets = offsets
        self.per_vob_id = per_vob_id
        self.mode = mode
        self.debug = debug

        if self.clip.get_frame(0).props["PVSSourcer"].decode("utf-8") == "core.d2v.Source" and per_vob_id and mode == 0:
            # decimate each vob id separately by splitting the clips apart before decimation
            # this allows you to specify different cycle+offsets match for each vob id
            vob_indexes = self.clip.get_frame(0).props["PVSVobIdIndexes"].decode("utf-8").split(" ")
            vob_indexes = [[int(y) for y in x.split("-")] for x in vob_indexes]
            clips = []
            for i, vob_index in enumerate(vob_indexes):
                clips.append(self._decimate(
                    core.std.Trim(
                        self.clip,
                        first=vob_index[0],
                        last=vob_index[1]
                    ),
                    mode=mode,
                    cycle=(
                        cycle[i] if len(cycle) - 1 >= i else cycle[0]
                    ) if isinstance(cycle, list) else cycle,
                    offsets=(
                        offsets[i] if len(offsets) - 1 >= i else offsets[0]
                    ) if isinstance(offsets[0], list) else offsets,
                    debug=debug
                ))
            self.clip = core.std.Splice(clips)
        else:
            self.clip = self._decimate(self.clip, mode, cycle, offsets, debug)

    @staticmethod
    def _decimate(clip, mode: int, cycle: int, offsets: List[int], debug: bool = False):
        if mode == 0:
            if isinstance(cycle, list):
                cycle = cycle[0]
            if isinstance(offsets[0], list):
                offsets = offsets[0]
            res = core.std.SelectEvery(clip, cycle=cycle, offsets=offsets)
            if debug:
                return core.std.FrameEval(
                    clip,
                    functools.partial(
                        lambda n, f, c: core.text.Text(
                            c,
                            " mode=%d cycle=%d offsets=%s fps=%d/%d \n" % (
                                mode, cycle, offsets, res.fps.numerator, res.fps.denominator
                            ) +
                            " offset=%d decimate=%s \n" % (n % cycle, (n % cycle) not in offsets),
                            alignment=1
                        ),
                        c=clip
                    ),
                    prop_src=clip
                )
            return res
        if mode == 1:
            if debug:
                return core.std.FrameEval(
                    clip,
                    functools.partial(
                        lambda n, f, c: core.text.Text(
                            c,
                            " mode=%d cycle=%d \n"
                            " Important: Please consider another mode. More information: git.io/avoid-tdecimate. \n"
                            " decimated_frame=%s \n" % (mode, cycle, f.props['VDecimateDrop'] == 1),
                            alignment=1
                        ),
                        c=clip
                    ),
                    prop_src=core.vivtc.VDecimate(clip, cycle=cycle, dryrun=True)
                )
            return core.vivtc.VDecimate(clip, cycle=cycle)
        raise ValueError("pvsfunc.decimate: Incorrect mode (%d), it must be an int value between 0-1" % mode)
