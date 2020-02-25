# std vs
from vapoursynth import core  # this may give a linter error, ignore
# std py
import functools

def decimate(clip, mode=0, cycle=5, offsets=[0, 1, 3, 4], debug=False):
    """
    Decimation is one of few kinds of pullup (reverse pulldown), this
    one is specifically to delete unwanted frames based on a cycle.
    :param mode: 0=SelectEvery, 1=VDecimate, use 0 if you can as it's more accurate
    :param cycle: how many frames to evaluate offsets on
    :param offsets: which frames to keep every `cycle` frames, zero-indexed
    """
    if mode == 0:
        if debug:
            clip = core.std.FrameEval(
                clip,
                functools.partial(
                    lambda n, f, c: core.text.Text(
                        c,
                        f"decimated_frame={(n % cycle) not in offsets}\n",
                        alignment=1
                    ),
                    c=clip
                ),
                prop_src=clip
            )
        return core.std.SelectEvery(clip, cycle=cycle, offsets=offsets)
    elif mode == 1:
        return core.vivtc.VDecimate(clip, cycle=cycle)
    else:
        raise ValueError("pvsfunc.decimate: Incorrect mode")

def debox(clip, aspect_ratio, mode=0, offset=0):
        """
        Crop out boxing by automatically evaluating the area
        based on a centered aspect ratio calculation
        mode: 0=Pillarboxing, 1=Letterboxing
        offset: move the crop window left/right (if mode=0) or
                up/down (if mode=1). Can be a + or - value.
        """
        aspect_ratio = aspect_ratio.split(":")
        aspect_ratio = aspect_ratio[0] / aspect_ratio[1]
        area = (clip.width - (clip.height * aspect_ratio)) / 2
        return core.std.CropRel(
            clip,
            left=area + offset if mode == 0 else 0,
            top=0 if mode == 0 else area + offset,
            right=area - offset if mode == 0 else 0,
            bottom=0 if mode == 0 else area - offset
        )
