# pvsfunc
PHOENiX's compilation of VapourSynth Script's and Functions

<p align="center">
<a href="https://python.org"><img src="https://img.shields.io/badge/python-3.6%2B-informational?style=flat-square" /></a>
<a href="https://github.com/rlaPHOENiX/pvsfunc/blob/master/LICENSE"><img alt="GitHub license" src="https://img.shields.io/github/license/rlaPHOENiX/pvsfunc?style=flat-square"></a>
<a href="https://www.codefactor.io/repository/github/rlaphoenix/pvsfunc"><img src="https://www.codefactor.io/repository/github/rlaphoenix/pvsfunc/badge" alt="CodeFactor" /></a>
<a href="https://www.codacy.com/manual/rlaPHOENiX/pvsfunc?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=rlaPHOENiX/pvsfunc&amp;utm_campaign=Badge_Grade"><img src="https://api.codacy.com/project/badge/Grade/574e843d9e044dcbbc2743cd8092148a"/></a>
<a href="https://github.com/rlaPHOENiX/pvsfunc/issues"><img alt="GitHub issues" src="https://img.shields.io/github/issues/rlaPHOENiX/pvsfunc?style=flat-square"></a>
<a href="http://makeapullrequest.com"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square"></a>
</p>

# Functions:

### Table of Contents

Function | Import
--- | ---
[MpegHelper](#mpeghelper-mpeghelperpy) | `from pvsfunc.mpeghelper import MpegHelper`

## MpegHelper ([mpeghelper.py](/pvsfunc/mpeghelper.py))
MpegHelper (class) is a convenience wrapper for loading and using MPEG videos. It's especially useful for DVD MPEG-1/2's.

`from pvsfunc.mpeghelper import MpegHelper`  
`MpegHelper(file_path[, bool rff=True, bool debug=False])`
* file_path: Path to a file to import as a clip. For MPEG (versions 1 and 2) it's best to use a d2v file.
* rff: Repeated Fields First. It's essentially a toggle switch for Pulldown. Only set this to false if you are sure it's entirely FILM or you don't want the non-FILM frames. In mostly FILM content, the non-FILM frames are typically post-production frames, like transition's and such.
* debug: Debug Mode, Enable it if you want to debug what's going on. On load, it will give you information on the loaded source like it's resolution and such which is gotten from MediaInfo (pymediainfo) in a small GUI text-box window. MpegHelper's function's will also provide debug information and may also print information into the frame itself via `core.text.Text()`.

### MpegHelper.deinterlace
Deinterlaces frames of a video only if the frame is interlaced. All information required for deinterlacing is gotten from the frame itself, which is why you don't need to specify Field Order (TFF/BFF). It deinterlaces using `vivtc.VFM` and only uses `havsfunc.QTGMC` if it could not find a field match. The entire process is much quicker and much more accurate than other deinterlacing methods and even supports working on videos with multiple scan-types and multiple scan-orders, like mixed scan DVD's which are common with Animated material.

`MpegHelper.deinterlace()`

### MpegHelper.decimate
Decimates (IVTC) the clip. Currently it internally uses `core.std.SelectEvery()` as I don't trust `core.vivtc.VDecimate` to be accurate, with my test's it often delete's wrong frames. I recommend you to change offsets to `[0, 1, 2, 3, 4]` (all frames kept) and check which frame tends to be the duplicate by previewing the clip and checking frame by frame. Using incorrect offsets will result in you deleting the wrong frame by mistake. Don't be afraid to change cycle if you believe it's necessary, though 3:2 pulldown is the most common and is a cycle of 5.

`MpegHelper.decimate([cycle=5, offsets=[0, 1, 3, 4], skip_checks=False])`
* cycle: Decimation Cycle, Takes n frames every n frames from the clip, and uses those frames for the offsets.
* offsets: Starting from index of 0 which is frame 1 of the cycle, this indicates which frames to KEEP from the cycle. For example, cycle of 5, and the default offsets (`[0, 1, 3, 4]`) will delete the 2nd frame every 5 frames (frames #2, #7, #12, #17 ... e.t.c)
* skip_checks: The function will do some preliminary checks to make sure the video actually needs decimating, if the checks make a mistake for your source, set this to True.

### MpegHelper.debox
Remove [Pillarboxing](https://wikipedia.org/wiki/Pillarbox), [Letterboxing](https://wikipedia.org/wiki/Letterboxing_(filming)) and [Windowboxing](https://wikipedia.org/wiki/Windowbox_(filmmaking)) from the video.

`MpegHelper.debox(aspect_ratio[, direction=0, offset=0])`
* aspect_ratio: The Aspect Ratio you wish to crop to, for example: `4/3` to crop to 4:3, `16/9` to crop to 16:9
* direction: The Direction you wish to crop. `0`=Landspace, `1`=Portrait. For example if the boxing is on the left and right (pillarboxing) use `0`, if the boxing is on the top and bottom (letterboxing) use `1`. If it's windowboxed, use `MpegHelper.debox` twice, first for landscape, then for portrait.
* offset: If the content isnt *right* in the center of the frame, you can modify offset to move the crop area. For example, if its a pillarbox (boxing on the left and right) and the content is 2 pixels towards the right (2 pixels away from being centered), use offset=2, if the content is 2 pixels towards the left, use offset=-2.