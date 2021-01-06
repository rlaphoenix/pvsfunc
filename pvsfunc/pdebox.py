from vapoursynth import core


class PDebox:
    """PDebox (PHOENiX Debox)."""

    def __init__(self, clip, aspect_ratio, mode=0, offset=0):
        """
        Remove Pillarboxing, Letterboxing or Windowboxing from the clip.

        This is done by calculating a crop area based on `aspect_ratio` against the clip width and height.
        It does it this way to reduce the annoyance of checking what values you need to crop on the edges for the
        desired result, when you most likely know the aspect ratio you wish the resulting crop to be. Saves you time.

        If it's Windowboxing, use this function twice, e.g. first for Pillarboxing, then for Letterboxing.

        :param clip: VapourSynth Clip (VideoNode) to debox.
        :param aspect_ratio: The Aspect Ratio you wish to crop to, e.g. `"4:3"` to crop to 4:3.
        :param mode: The Direction you wish to crop. `0`=Pillarboxing, `1`=Letterboxing.
        :param offset: If the content isn't exactly in the center of the frame.
        """
        aspect_ratio = [int(n) for n in aspect_ratio.split(":")]
        aspect_ratio = aspect_ratio[0] / aspect_ratio[1]
        area = (clip.width - (clip.height * aspect_ratio)) / 2
        self.clip = core.std.CropRel(
            clip,
            left=area + offset if mode == 0 else 0,
            top=0 if mode == 0 else area + offset,
            right=area - offset if mode == 0 else 0,
            bottom=0 if mode == 0 else area - offset
        )
