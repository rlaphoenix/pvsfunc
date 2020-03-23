# std vs
from vapoursynth import core  # this may give a linter error, ignore
# std py
import functools

def decimate(clip, mode=0, cycle=5, offsets=[0, 1, 3, 4], debug=False):
    """
    IVTC (Inverse-telecine) the clip using decimation (frame deletion).
    This would commonly be used to revert the telecine process of FILM
    to NTSC but can be used for other rate changes.
    :param mode: 0=core.std.SelectEvery, 1=core.vivtc.VDecimate, If your
    source uses a constant offsets value throughout the entire source I
    recommend using mode=0 and ensure offsets are correct. If you need
    automation or the offsets tend to change throughout the source, use
    mode=1.
    :param cycle: Chunks the clip into `n` frames, then deletes frames
    specified by `offsets` (if any).
    :param offsets: *Only used if mode=0* Starting from index of 0 which
    is frame 1 of the cycle, this indicates which frames to KEEP from the
    cycle. For example, cycle of 5, and the default offsets (`[0, 1, 3, 4]`)
    will delete the 3rd frame (because index 2 isn't in the list) every 5
    (cycle) frames.
    :param debug: Print debugging information
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
        Remove Pillarboxing, Letterboxing or Windowboxing from the video
        by calculating a crop area based on `aspect_ratio` calculated against
        clip width and height. If it's windowboxed, use this function twice,
        first for Pillarboxing, then for Letterboxing.
        :param aspect_ratio: The Aspect Ratio you wish to crop to, for example:
        `4:3` to crop to 4:3, `16:9` to crop to 16:9
        :param mode: The Direction you wish to crop. `0`=Pillarboxing (would crop
        sides), `1`=Letterboxing (would crop top/bottom).
        :param offset: If the content isnt exactly in the center of the frame,
        you can modify offset to move the crop area. For example, if its a
        mode=0 (boxing on the left and right) and the content is 2 pixels
        towards the right (2 pixels away from being centered), use offset=2,
        if the content is 2 pixels towards the left, use offset=-2
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

def calculate_aspect_ratio(width: int, height: int) -> str:
    def gcd(a, b):
        """The GCD (greatest common divisor) is the highest number that evenly divides both width and height."""
        return a if b == 0 else gcd(b, a % b)
    r = gcd(width, height)
    return f"{int(width / r)}:{int(height / r)}"
