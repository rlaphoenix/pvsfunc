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

| Function                                        | Import                                            |
| ---                                             | ---                                               |
| [MpegProcessor](#mpegprocessor-mpegprocessorpy) | `from pvsfunc.mpegprocessor import MpegProcessor` |
| [decimate](#decimate-initpy)                    | `from pvsfunc.__init__ import decimate`           |
| [debox](#debox-initpy)                          | `from pvsfunc.__init__ import debox`              |

### MpegProcessor ([mpegprocessor.py](/pvsfunc/mpegprocessor.py))
MpegProcessor (class) is a convenience wrapper for loading and using MPEG videos. It's primary function is to handle the loading and handle video fields to return a CFR (Constant frame-rate) progressive video.

`from pvsfunc.mpegprocessor import MpegProcessor`  
`MpegProcessor(filepath[, dict source_cfg={}, str dgindex_path="DGIndex.exe", bool debug=False])`
* filepath: Path to a file to import. An MKV file is recommended no matter what the video codec is.
* source_cfg: A dictionary of key=value pairs that will be unpacked and provided to whatever clip Sourcing function get's used. You must provide a dictionary where it's key's are the source function, e.g. `{"core.d2v.Source": { "rff": True }, "core.ffms2.Source": { "alpha": False }}`
* dgindex_path: A filepath to DGIndex. On Windows if the exe is in your Environment Path, you may simply put "DGIndex" or "DGIndex.exe".
* debug: Debug Mode, Enable it if you want to debug frame information.

#### MpegProcessor.deinterlace
Deinterlaces frames of a video only if the frame is interlaced. All information required for deinterlacing is gotten from the frame itself, which is why you don't need to specify Field Order (tff=None is automated). It deinterlaces interlaced frames using `vivtc.VFM` and only uses `havsfunc.QTGMC` if it could not find a field match. The entire process is much quicker and much more accurate than other deinterlacing methods and even supports working on videos with multiple scan-types, frame-rates and scan-orders. The output will be CFR (Constant frame-rate).

`MpegHelper.deinterlace([dict vfm_cfg={}, dict qtgmc_cfg={}, bool tff=None])`
* vfm_cfg: key=value settings to pass to core.vivtc.VFM as unpacked arguments (e.g. `{"order": 1, "mode": 5}`). It defaults to `{"order": based on tff arg, "field": 2, "mode": 0}`.
* qtgmc_cfg: key=value settings to pass to havsfunc.QTGMC as unpacked arguments (e.g. `{"FPSDivisor": 1, "Preset": "Medium"}`). It defaults to Single-rate Placebo optimized output based on tff, See code for actual settings used, it will be very slow but great quality wise.
* tff: Wheter to use Top-Field-First or not. None will automatically decide based on the first frame if possible, otherwise it defaults to True.

### decimate ([__init__.py](/pvsfunc/__init__.py))
IVTC (Inverse-telecine) the clip using decimation (frame deletion). This would commonly be used to revert the telecine process of FILM to NTSC but can be used for other rate changes.

`from pvsfunc.__init__ import decimate`  
`decimate([int mode=0, int cycle=5, list offsets=[0, 1, 3, 4], bool debug=False])`
* mode: 0=core.std.SelectEvery, 1=core.vivtc.VDecimate, If your source uses a constant offsets value throughout the entire source I recommend using mode=0 and ensure offsets are correct. If you need automation or the offsets tend to change throughout the source, use mode=1.
* cycle: Chunks the clip into `n` frames, then deletes frames specified by `offsets` (if any).
* offsets: *Only used if mode=0* Starting from index of 0 which is frame 1 of the cycle, this indicates which frames to KEEP from the cycle. For example, cycle of 5, and the default offsets (`[0, 1, 3, 4]`) will delete the 3rd frame (because index 2 isn't in the list) every 5 (cycle) frames.
* debug: Print debugging information

### debox ([__init__.py](/pvsfunc/__init__.py))
Remove [Pillarboxing](https://wikipedia.org/wiki/Pillarbox), [Letterboxing](https://wikipedia.org/wiki/Letterboxing_(filming)) or [Windowboxing](https://wikipedia.org/wiki/Windowbox_(filmmaking)) from the video by calculating a crop area based on `aspect_ratio` calculated against clip width and height. If it's windowboxed, use this function twice, first for Pillarboxing, then for Letterboxing.

`from pvsfunc.__init__ import debox`  
`debox(str aspect_ratio[, int mode=0, int offset=0])`
* aspect_ratio: The Aspect Ratio you wish to crop to, for example: `4:3` to crop to 4:3, `16:9` to crop to 16:9
* mode: The Direction you wish to crop. `0`=Pillarboxing (would crop sides), `1`=Letterboxing (would crop top/bottom).
* offset: If the content isnt *exactly* in the center of the frame, you can modify offset to move the crop area. For example, if its a mode=0 (boxing on the left and right) and the content is 2 pixels towards the right (2 pixels away from being centered), use offset=2, if the content is 2 pixels towards the left, use offset=-2
