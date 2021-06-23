import math
from itertools import groupby
from operator import itemgetter
from typing import Iterable, List


def get_standard(aspect: float) -> str:
    """Convert an aspect float to a standard string."""
    return {
        0: "?",
        24 / 1: "FILM",
        25 / 1: "PAL",
        50 / 1: "PALi",
        30000 / 1001: "NTSC",
        60000 / 1001: "NTSCi",
        24000 / 1001: "NTSC (FILM)"
    }[aspect]


def calculate_aspect_ratio(width: int, height: int) -> str:
    """Calculate the aspect-ratio gcd string from resolution."""
    r = math.gcd(width, height)
    return "%d:%d" % (int(width / r), int(height / r))


def calculate_par(width: int, height: int, aspect_ratio_w: int, aspect_ratio_h: int) -> str:
    """Calculate the pixel-aspect-ratio string from resolution."""
    par_w = height * aspect_ratio_w
    par_h = width * aspect_ratio_h
    par_gcd = math.gcd(par_w, par_h)
    par_w = int(par_w / par_gcd)
    par_h = int(par_h / par_gcd)
    return "%d:%d" % (par_w, par_h)


def list_select_every(data: list, cycle: int, offsets: (set, Iterable[int]), inverse: bool = False) -> list:
    """
    Same as VapourSynth's core.std.SelectEvery but for generic list data, and inverse.
    Don't use this as a replacement to core.std.SelectEvery, this should only be used on generic list data.
    """
    if not isinstance(cycle, int) or cycle < 1:
        raise ValueError("Cycle must be an int greater than or equal to 1.")
    if not offsets:
        raise ValueError("Offsets must not be empty.")
    if not isinstance(offsets, set):
        offsets = set(offsets)
    if not isinstance(inverse, bool) and inverse not in (0, 1):
        raise ValueError("Inverse must be a bool or int bool.")

    if not data:
        return data

    return [x for n, x in enumerate(data) if (n % cycle in offsets) ^ inverse]


def group_by_int(data: List[int]) -> list:
    """
    Group a list of integers into sub-lists.
    e.g. [1,2,3,5,6,7,9]: [[1,2,3],[5,6,7],[9]]
    """
    for k, g in groupby(enumerate(data), lambda x: x[0] - x[1]):
        yield list(map(itemgetter(1), g))
