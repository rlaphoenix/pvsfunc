# std vs
from vapoursynth import core
import vapoursynth as vs
# std py
import functools


def decimate(clip, per_vob_id=True, mode=0, cycle=5, offsets=[0, 1, 3, 4], debug=False):
    """
    IVTC (Inverse-telecine) the clip using decimation (frame deletion).
    This would commonly be used to revert the telecine process of FILM
    to NTSC but can be used for other rate changes.

    :param clip: VapourSynth Clip (VideoNode) to decimate
    :param mode: 0=core.std.SelectEvery (recommended), 1=core.vivtc.VDecimate (be warned; its inaccurate!)
    :param cycle: Defines the amount of frames to calculate offsets on at a time.
    :param offsets: Mode 0's offsets zero-indexed list. This indicates which frames to KEEP from the cycle.
    :param debug: Skip decimation and print debugging information. Useful to check if the frames that the cycle
    and offset settings you have provided are correct and actually decimate the right frames.
    """
    def decimate_(clip, mode, cycle, offsets, debug):
        if mode < 0 or mode > 1:
            raise ValueError(f"pvsfunc.decimate: Incorrect mode ({mode}), it must be an int value between 0-1")
        if mode == 0:
            if isinstance(cycle, list):
                cycle = cycle[0]
            if isinstance(offsets[0], list):
                offsets = offsets[0]
            if debug:
                return core.std.FrameEval(
                    clip,
                    functools.partial(
                        lambda n, f, c: core.text.Text(
                            c,
                            f" mode={mode} cycle={cycle} offsets={offsets} \n"
                            f" decimated_frame={(n % cycle) not in offsets} \n",
                            alignment=1
                        ),
                        c=clip
                    ),
                    prop_src=clip
                )
            return core.std.SelectEvery(clip, cycle=cycle, offsets=offsets)
        if mode == 1:
            if debug:
                return core.std.FrameEval(
                    clip,
                    functools.partial(
                        lambda n, f, c: core.text.Text(
                            c,
                            f" mode={mode} cycle={cycle} \n"
                            " Important: Please consider another mode. More information: git.io/avoid-tdecimate. \n"
                            f" decimated_frame={f.props['VDecimateDrop'] == 1} \n",
                            alignment=1
                        ),
                        c=clip
                    ),
                    prop_src=core.vivtc.VDecimate(clip, cycle=cycle, dryrun=True)
                )
            return core.vivtc.VDecimate(clip, cycle=cycle)
    
    if per_vob_id:
        # decimate each vob id seperately by splitting the clips apart before decimation
        # this allows you to specify different cycle+offsets match for each vob id
        vob_indexes = clip.get_frame(0).props["PVSVobIdIndexes"].decode("utf-8").split(" ")
        vob_indexes = [[int(y) for y in x.split("-")] for x in vob_indexes]
        clips = []
        for i, vob_index in enumerate(vob_indexes):
            clips.append(decimate_(
                core.std.Trim(
                    clip,
                    first=vob_index[0],
                    last=vob_index[1]
                ),
                mode=mode,
                cycle=(
                    cycle[i] if len(cycle)-1 >= i else cycle[0]
                ) if isinstance(cycle, list) else cycle,
                offsets=(
                    offsets[i] if len(offsets)-1 >= i else offsets[0]
                ) if isinstance(offsets[0], list) else offsets,
                debug=debug
            ))
        return core.std.Splice(clips)
    return decimate_(clip, mode, cycle, offsets, debug)


def debox(clip, aspect_ratio, mode=0, offset=0):
    """
    Remove Pillarboxing, Letterboxing or Windowboxing from the video
    by calculating a crop area based on `aspect_ratio` calculated against
    clip width and height. If it's Windowboxing, use this function twice,
    first for Pillarboxing, then for Letterboxing.

    :param clip: VapourSynth Clip (VideoNode) to debox
    :param aspect_ratio: The Aspect Ratio you wish to crop to, e.g. `"4:3"` to crop to 4:3
    :param mode: The Direction you wish to crop. `0`=Pillarboxing, `1`=Letterboxing.
    :param offset: If the content isn't exactly in the center of the frame
    """
    aspect_ratio = [int(n) for n in aspect_ratio.split(":")]
    aspect_ratio = aspect_ratio[0] / aspect_ratio[1]
    area = (clip.width - (clip.height * aspect_ratio)) / 2
    return core.std.CropRel(
        clip,
        left=area + offset if mode == 0 else 0,
        top=0 if mode == 0 else area + offset,
        right=area - offset if mode == 0 else 0,
        bottom=0 if mode == 0 else area - offset
    )
