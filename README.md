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

## Classes

| Class                                           | Import                                            |
| ----------------------------------------------- | ------------------------------------------------- |
| [PSourcer](#psourcer-psourcerpy)                | `from pvsfunc.psourcer import PSourcer`           |
| [PDeinterlacer](#pdeinterlacer-pdeinterlacerpy) | `from pvsfunc.pdeinterlacer import PDeinterlacer` |

### PSourcer ([psourcer.py](/pvsfunc/psourcer.py))

PSourcer (class) is a convenience wrapper for loading video files to clip variables. It's purpose is to load an input file path with the most optimal clip source based on the file. For example for an MPEG-2 video file (e.g. DVD file) it will load using core.d2v.Source (and generate a d2v if needed too!), whereas for an MPEG-4/AVC/H.264 video it will load using core.ffms2.Source.

`from pvsfunc.psourcer import PSourcer`
`PSourcer(str file_path)`

- file_path: Path to a file to import. Don't worry about which type of container (if any) you use.

The following must be installed and added to the system environment variables/PATH.

- [mkvextract from MKVToolNix](https://mkvtoolnix.download)
- [DGIndex from DGMpgDec v1.5.8](http://rationalqm.us/dgmpgdec/dgmpgdec.html) (dont worry it works with WINE on linux)

\* _important: if your on linux, add DGIndex to path via `/etc/profile.d/` instead of `~/.profile`, `~/.bashrc` e.t.c as those are SHELL-exclusive PATH's, not global system-wide._

### PDeinterlacer ([pdeinterlacer.py](/pvsfunc/pdeinterlacer.py))

PDeinterlacer (class) is a convenience wrapper for deinterlacing clips. Its unique feature is it can handle mixed scan-type videos. It will always return a progressive and CFR (constant frame-rate) video. It's similar to a retail DVD player as it deinterlaces only if the frame is marked as interlaced, no metrics or guessing is involved.

Just to clarify this is a deinterlacer wrapper, not a full-fledged deinterlacer, by default it interally uses QTGMC but you can change the kernel.

`from pvsfunc.pdeinterlacer import PDeinterlacer`  
`PDeinterlacer(clip[, bool tff=True, func kernel=None, dict kernel_args=None, bool debug=False])`

- clip: Clip to deinterlace, this must be a clip loaded with PSourcer as it requires some of the props that PSourcer applies to clips
- tff: Top-Field-First
- kernel: Deinterlacer Kernel Function to use for deinterlacing. It defaults to `havsfunc.QTGMC`.
- kernel_args: Arguments to pass to the Kernel Function when deinterlacing.
- debug: Debug Mode, Enable it if you want to debug frame information.

## Functions

| Function                                        | Import                                            |
| ----------------------------------------------- | ------------------------------------------------- |
| [decimate](#decimate-initpy)                    | `from pvsfunc.__init__ import decimate`           |
| [debox](#debox-initpy)                          | `from pvsfunc.__init__ import debox`              |

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
