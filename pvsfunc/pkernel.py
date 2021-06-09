from typing import List, Union

import vapoursynth as vs
from vapoursynth import core


class PKernel:
    """
    Custom kernels that can be used for Deinterlacing.
    Don't expect QTGMC killers or even anything traditional. Most likely all
    that will be in here is weird custom stuff I'm fiddling with, e.g. Machine
    learning in-painting (see void_weave).
    """

    @classmethod
    def void_weave(cls, clip: vs.VideoNode, tff: bool, color: List[Union[int, float]], bob=False) -> vs.VideoNode:
        """
        Weaves a 255(rgb) #00ff00(hex) green as the 2nd field of every field.
        The purpose of this would be for machine learning in-painting over the green
        rows with interpreted pixel data for machine learning deinterlacing.

        <!> clip's color-space will be converted to RGB24 using core.resize.Point,
                As most machine-learning programs rely on reading RGB data.
        """
        # TODO: figure out a way to get this working without having to convert color-space at all
        if not clip.format or clip.format.name != "RGB24":
            clip = core.resize.Point(clip, format=vs.RGB24)

        clip = core.std.SeparateFields(clip, tff=tff)
        clip = core.std.Interleave([
            clip,
            core.std.BlankClip(clip, color=color, keep=0)
        ])
        clip = core.std.DoubleWeave(clip, tff=tff)
        clip = core.std.SelectEvery(clip, cycle=2, offsets=0)

        if bob:
            # vertically align every even (2nd) field with every odd (1st) field
            # by adding a 1px row of black pixels on the top, and removing from the bottom
            odd = core.std.SelectEvery(clip, cycle=2, offsets=0)
            even = core.std.SelectEvery(clip, cycle=2, offsets=1)
            even = core.std.AddBorders(even, top=1, color=color)
            even = core.std.Crop(even, bottom=1)
            return core.std.Interleave([odd, even])

        return core.std.SelectEvery(clip, cycle=2, offsets=0)
