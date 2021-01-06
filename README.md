# pvsfunc

pvsfunc (PHOENiX's VapourSynth Functions) is my compilation of VapourSynth Script's, Functions, and Helpers.

[![Build Tests](https://img.shields.io/github/workflow/status/rlaPHOENiX/pvsfunc/Version%20test?label=Python%203.5%2B%20builds)](https://github.com/rlaPHOENiX/pvsfunc/actions?query=workflow%3A%22Version+test%22)
[![License](https://img.shields.io/github/license/rlaPHOENiX/pvsfunc?style=flat)](https://github.com/rlaPHOENiX/pvsfunc/blob/master/LICENSE)
[![DeepSource](https://deepsource.io/gh/rlaPHOENiX/pvsfunc.svg/?label=active+issues&show_trend=true)](https://deepsource.io/gh/rlaPHOENiX/pvsfunc/?ref=repository-badge)
[![Issues](https://img.shields.io/github/issues/rlaPHOENiX/pvsfunc?style=flat)](https://github.com/rlaPHOENiX/pvsfunc/issues)
[![PR's Accepted](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat)](https://makeapullrequest.com)

* * *

## Installation

1.  Install VapourSynth first! (this is different to the pypi/pip `vapoursynth` package!)
2.  `pip install pvsfunc`
3.  Make sure you have all the dependencies listed below installed.
4.  It's as simple as that!

### Dependencies

| Input File Codec | Sourcer Used                    | Dependencies                                             |
| ---------------- | ------------------------------- | -------------------------------------------------------- |
| MPEG-1, MPEG-2   | [d2vsource][d2vs] (d2v)         | [DGIndex >=v1.5.8][dg] **†1**, [mkvextract][mkvnix] **†2** |
| Any other codec  | [L-SMASH-WORKS][lsmash] (lsmas) | [mkvmerge][mkvnix] **†3**                                |

Installation of the sourcer cores:

-   Windows: `vsrepo install package_name` - You can get package names by searching for it on <https://vsdb.top>
-   Linux: You probably know the drill. Check your package repo's or compile it.
-   Mac: No idea how the python/vapoursynth eco-system works, sorry.

Information for Linux users:

-   If any windows-only program is a dependency, then it is supported by wine and confirmed to be safe to use with full compatability.
-   Add DGIndex to path via `/etc/profile.d/` instead of `~/.profile`, `~/.bashrc` e.t.c as those are SHELL-exclusive PATH's, not global system-wide.

**†1** Only used if the file path is not to a .d2v file, or there's no corresponding .d2v file next to the input file. Please note that this script uses this to make specifically configured .d2v files with specific settings. Supplying you're own .d2v files is unsafe.

**†2** Only used if you're providing a file that isnt a .mpeg, .mpg, or .m2v (e.g. mkv, mp4) and there's no corresponding .d2v file. For efficiency and safety files are demuxed out of the container so DGIndex is reading a direct MPEG stream.

**†3** Will only be used if the container has a manual frame rate set that differs to the encoded frame rate. For L-SMASH-WORKS to index the file with the correct source frame rate. PSourcer uses mkvmerge to re-mux the file, with the container-set FPS removed.

* * *

## Building

This project is firmly requiring the use of Python PIP with [PEP 517][pep517] support. This means you need `pip >= 19`
[(ref)][pip19].

Considering version `19.0` released on the 22nd of January 2019, it isn't much of an ask in my opinion, when you end up
with an overall much smoother build experience.

Once you have pip with PEP 517 support, it's as simple as 3 calls:

    pip install build
    git clone https://github.com/rlaPHOENiX/pvsfunc && cd pvsfunc
    python -m build

To install the built project, install the .whl file available in /dist, e.g. `pip install dist/*.whl`

If you want to simply install from the source, instead of `python -m build` run `pip install .`

[pep517]: https://www.python.org/dev/peps/pep-0517

[pip19]: https://pip.pypa.io/en/stable/news/#id415

* * *

## License

This project is released under the GNU GENERAL PUBLIC LICENSE Version 3 (GPLv3) license.
Please read and agree to the license before use, it can be found in the [LICENSE](LICENSE) file.

* * *

## Documentation

| Class                                           | Import                                            |
| ----------------------------------------------- | ------------------------------------------------- |
| [PSourcer](#psourcer-psourcerpy)                | `from pvsfunc import PSourcer`                    |
| [PDeinterlacer](#pdeinterlacer-pdeinterlacerpy) | `from pvsfunc import PDeinterlacer`               |
| [PDecimate](#pdecimate-pdecimatepy)             | `from pvsfunc import PDecimate`                   |
| [PDebox](#pdebox-pdeboxpy)                      | `from pvsfunc import PDebox`                      |

### PSourcer ([psourcer.py](/pvsfunc/psourcer.py))

PSourcer (class) is a convenience wrapper for loading video files to clip variables. It's purpose is to load an input file path with the most optimal clip source based on the file. For example for an MPEG-2 video file (e.g. DVD file) will load using `core.d2v.Source` (and generate an optimized d2v if needed too!), whereas an MPEG-4/AVC/H.264 video will load using `core.lsmas.LWLibavSource`.

`from pvsfunc import PSourcer`  
`PSourcer(str file_path[, bool debug=False])`

-   file_path: Path to a file to import. Don't worry about which type of container (if any) you use.
-   debug: Use core.text to print verbose information about the file and how it has been loaded.

### PDeinterlacer ([pdeinterlacer.py](/pvsfunc/pdeinterlacer.py))

PDeinterlacer (class) is a convenience wrapper for deinterlacing clips. Its unique feature is it can handle variable scan-type videos and therefore variable frame-rate videos as well. It will always return a progressive and CFR (constant frame-rate) video. It's similar to a retail DVD player as it deinterlaces only if the frame is marked as interlaced, no metrics or guessing is involved.

Just to clarify this is a deinterlacer wrapper, not it's own deinterlacer kernel. You must supply it with a kernel to use. To reduce dependencies, no base kernel is defaulted.

`from pvsfunc import PDeinterlacer`  
`PDeinterlacer(clip, func kernel[, dict kernel_args=None, bool debug=False])`

-   clip: Clip to deinterlace, this must be a clip loaded with PSourcer as it requires some of the props that PSourcer applies to clips.
-   kernel: Deinterlacer Kernel Function to use for deinterlacing. If you don't know which kernel to use, [QTGMC](http://avisynth.nl/index.php/QTGMC) is a good bet but may not be the answer for your specific source. For example, QTGMC isn't the best for Animated sources, or sources that have consistent amount of duplicate frames (e.g. animation).
-   kernel_args: Arguments to pass to the Kernel Function when deinterlacing.
-   debug: Debug Mode, Enable it if you want to debug frame information.

### PDecimate ([pdecimate.py](/pvsfunc/pdecimate.py))

PDecimate (class) is a convenience wrapper for Decimating operations. It can be used to delete frames in a variable or constant pattern, either by manual definition or by automated means (via VDecimate however, <https://git.io/avoid-tdecimate>). Decimation is often used for IVTC purposes to remove constant pattern pulldown frames (duplicate frames for changing frame rate).

`from pvsfunc import PDecimate`  
`PDecimate(clip, int cycle, list<int> offsets[, per_vob_id=True, mode=0, debug=False])`

-   clip: Clip to decimate, this must be a clip loaded with PSourcer as it requires some of the props that PSourcer applies to clips.
-   cycle: Defines the amount of frames to calculate offsets on at a time.
-   offset: Mode 0's offsets are a zero-indexed list. This indicates which frames to KEEP from the cycle. Set to `None` when using mode=1.
-   per_vob_id: When Clip is a DVD-Video Object (.VOB): Reset the cycle every time the VOB Cell changes.
-   mode: 0=core.std.SelectEvery (recommended), 1=core.vivtc.VDecimate (be warned; its inaccurate!)
-   debug: Skip decimation and print debugging information. Useful to check if the frames that the cycle and offset settings you have provided are correct and actually decimate the right frames.

### PDebox ([pdebox.py](/pvsfunc/pdebox.py))

PDebox (class) is a convenience wrapper for Deboxing operations. Ever encounter sources where there's black bars on the top and bottom, sides, or both? That means it's Letterboxed, Pillarboxed, or Windowboxed respectively. PDebox helps you remove Letterboxing and Pillarboxing, and through that Windowboxing too.

`from pvsfunc import PDebox`  
`PDebox(clip, str aspect_ratio, [int mode=0, offset=0])`

-   clip: Clip to debox.
-   aspect_ratio: Aspect Ratio you wish to crop to, in string form, e.g. `"4:3"`.
-   mode: Mode of operation, 0=Pillarboxing, 1=Letterboxing.
-   offset: If the boxing is slightly more on one side than the other, than you can set this offset appropriately to move the area that PDebox returns. e.g. mode=0, and there's 1px more of a pillar on the right than on the left, the offset should be -1.

[dg]: http://rationalqm.us/dgmpgdec/dgmpgdec.html

[mkvnix]: https://mkvtoolnix.download

[lsmash]: https://github.com/VFR-maniac/L-SMASH-Works

[d2vs]: https://github.com/dwbuiten/d2vsource
