# pvsfunc

PHOENiX's compilation of VapourSynth Script's and Functions

`pip install pvsfunc`

<p align="center">
<a href="https://python.org"><img src="https://img.shields.io/badge/python-3.6%2B-informational?style=flat-square" /></a>
<a href="https://github.com/rlaPHOENiX/pvsfunc/blob/master/LICENSE"><img alt="GitHub license" src="https://img.shields.io/github/license/rlaPHOENiX/pvsfunc?style=flat-square"></a>
<a href="https://www.codefactor.io/repository/github/rlaphoenix/pvsfunc"><img src="https://www.codefactor.io/repository/github/rlaphoenix/pvsfunc/badge" alt="CodeFactor" /></a>
<a href="https://www.codacy.com/manual/rlaPHOENiX/pvsfunc?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=rlaPHOENiX/pvsfunc&amp;utm_campaign=Badge_Grade"><img src="https://api.codacy.com/project/badge/Grade/574e843d9e044dcbbc2743cd8092148a"/></a>
<a href="https://github.com/rlaPHOENiX/pvsfunc/issues"><img alt="GitHub issues" src="https://img.shields.io/github/issues/rlaPHOENiX/pvsfunc?style=flat-square"></a>
<a href="http://makeapullrequest.com"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square"></a>
</p>

## Functions

| Function                     | Import                                  |
| ---------------------------- | --------------------------------------- |
| [PDeint](#pdeint-pdeintpy)   | `from pvsfunc.pdeint import PDeint`     |
| [decimate](#decimate-initpy) | `from pvsfunc.__init__ import decimate` |
| [debox](#debox-initpy)       | `from pvsfunc.__init__ import debox`    |

### PDeint ([pdeint.py](/pvsfunc/pdeint.py))

PDeint (class) is a convenience wrapper for loading and using MPEG videos. Its primary function is to handle the loading and handle video fields to return a CFR (Constant frame-rate) progressive video.

It's similar to a retail DVD player as it deinterlaces only if the frame is marked as interlaced, no metrics or guessing is involved.

`from pvsfunc.pdeint import PDeint`  
`PDeint(file_path[, dict source_cfg={}, str dgindex_path="DGIndex.exe", bool debug=False])`

- file_path: Path to a file to import. An MKV file is recommended no matter what the video codec is.
- source_cfg: A dictionary of key=value pairs that will be unpacked and provided to whatever clip Sourcing function get's used. You must provide a dictionary where it's key's are the source function, e.g. `{"core.d2v.Source": { "rff": True }, "core.ffms2.Source": { "alpha": False }}`
- dgindex_path: A filepath to DGIndex. On Windows if the exe is in your Environment Path, you may simply put "DGIndex" or "DGIndex.exe".
- debug: Debug Mode, Enable it if you want to debug frame information.

#### PDeint.deinterlace

By default it does not start the deinterlace process as PDeint can also be used as a general video sourcer. Run this function to start the deinterlacing.
Deinterlaces frames of a video only if the frame is interlaced. All information required for deinterlacing is gotten from the frame itself, which is why you don't need to specify Field Order (tff=None is automated). If a frame needs deinterlacing it will use whatever kernel and kernel arguments you supply, which will be havsfunc's QTGMC by default. This supports working on videos with mixed scan-types and frame-rates (as long as the only frames with Pulldown metadata differ in frame-rate). The output will be always be CFR (Constant frame-rate).

`PDeint.deinterlace([bool tff=True, func kernel=None, string kernel_clip_key=None, dict kernel_cfg=None, bool debug=False])`

- tff: Deinterlace the Top-Field-First.
- kernel: The function to use as a Deinterlacer. This will default to `havsfunc.QTGMC`.
- kernel_clip_key: The argument name that asks for the input clip, e.g. `havsfunc.QTGMC` asks for `Input` to be the input clip.
- kernel_cfg: The arguments for `kernel` as a Key-Value dictionary.
- debug: Debug mode, this will display various information allowing you to better understand what the script is doing.

### decimate ([**init**.py](/pvsfunc/__init__.py))

IVTC (Inverse-telecine) the clip using decimation (frame deletion). This would commonly be used to revert the telecine process of FILM to NTSC but can be used for other rate changes.

`from pvsfunc.__init__ import decimate`  
`decimate([int mode=0, int cycle=5, list offsets=[0, 1, 3, 4], bool debug=False])`

- mode: 0=core.std.SelectEvery, 1=core.vivtc.VDecimate, If your source uses a constant offsets value throughout the entire source I recommend using mode=0 and ensure offsets are correct. If you need automation or the offsets tend to change throughout the source, use mode=1.
- cycle: Chunks the clip into `n` frames, then deletes frames specified by `offsets` (if any).
- offsets: _Only used if mode=0_ Starting from index of 0 which is frame 1 of the cycle, this indicates which frames to KEEP from the cycle. For example, cycle of 5, and the default offsets (`[0, 1, 3, 4]`) will delete the 3rd frame (because index 2 isn't in the list) every 5 (cycle) frames.
- debug: Print debugging information

### debox ([**init**.py](/pvsfunc/__init__.py))

Remove [Pillarboxing](https://wikipedia.org/wiki/Pillarbox), [Letterboxing](<https://wikipedia.org/wiki/Letterboxing_(filming)>) or [Windowboxing](<https://wikipedia.org/wiki/Windowbox_(filmmaking)>) from the video by calculating a crop area based on `aspect_ratio` calculated against clip width and height. If it's windowboxed, use this function twice, first for Pillarboxing, then for Letterboxing.

`from pvsfunc.__init__ import debox`  
`debox(str aspect_ratio[, int mode=0, int offset=0])`

- aspect_ratio: The Aspect Ratio you wish to crop to, for example: `4:3` to crop to 4:3, `16:9` to crop to 16:9
- mode: The Direction you wish to crop. `0`=Pillarboxing (would crop sides), `1`=Letterboxing (would crop top/bottom).
- offset: If the content isnt _exactly_ in the center of the frame, you can modify offset to move the crop area. For example, if its a mode=0 (boxing on the left and right) and the content is 2 pixels towards the right (2 pixels away from being centered), use offset=2, if the content is 2 pixels towards the left, use offset=-2
