# pvsfunc

pvsfunc (PHOENiX's VapourSynth Functions) is my compilation of VapourSynth Scripts, Functions, and Helpers.

[![Build Tests](https://github.com/rlaphoenix/pvsfunc/actions/workflows/ci.yml/badge.svg)](https://github.com/rlaphoenix/pvsfunc/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/rlaphoenix/pvsfunc?style=flat)](https://github.com/rlaphoenix/pvsfunc/blob/master/LICENSE)
[![DeepSource](https://deepsource.io/gh/rlaphoenix/pvsfunc.svg)](https://deepsource.io/gh/rlaphoenix/pvsfunc)
[![Issues](https://img.shields.io/github/issues/rlaphoenix/pvsfunc?style=flat)](https://github.com/rlaphoenix/pvsfunc/issues)
[![PR's Accepted](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat)](https://makeapullrequest.com)

## Installation

Install [VapourSynth] first! (this is different to the pypi/pip `vapoursynth` python wrapper!)

    pip install --user pvsfunc

Done! However, there are further dependencies listed below that you may need to install depending on the classes you
intend to use, and your use-case. Don't forget to install them if needed!

  [VapourSynth]: <https://www.vapoursynth.com/doc/installation.html>

## Building

Building from source requires [Poetry](https://python-poetry.org).  
Simply run `poetry install` or `poetry build` for distribution wheel and source packages.

## PD2V

PD2V has been moved to its own repository and renamed MPGG, <https://github.com/rlaphoenix/mpgg>.

## PLS

Convenience class for working with L-SMASH-WORKS LWI project files. Includes source loading and deinterlacing.
More features are to be implemented in the future once a Python-based LWI project parser is available.

Refer to PD2Vs example usage as it's very similar to how PLS is used.

### Dependencies

- [lsmash] (core.lsmas) VapourSynth plugin
- [mkvmerge] Only required if input file has a container-set frame rate that differs to the encoded frame rate

To install [lsmash] it's as simple as `vsrepo install lsmas` on Windows. Other Operating System user's know the drill,
go check your package repository's or compile it yourself.

Make sure [mkvmerge] is available on your environment path and has execution permissions. Note Linux Users: Add to
system profile path, not terminal/rc path.

  [mkvmerge]: https://mkvtoolnix.download
  [lsmash]: https://github.com/VFR-maniac/L-SMASH-Works

## PDebox

Lightweight class to apply de-boxing based on an output aspect-ratio. Similar scripts would annoyingly want you to
just crop in yourself which is incredibly annoying.

## PDecimate

Decimate (delete) frames in a specified pattern using cycle and offsets. This is typically used for Inverse-Telecine
purposes.

Decimation may often be done for IVTC purposes to remove constant pattern pulldown frames.

## PKernel

Kernel storage class for any custom Deinterlacing kernels I'm working on or tinkering with that you may want to use.
Just know that they are most likely not the type of deinterlacing you may expect, as it's generally a playground for
looking into strange tactics of deinterlacing.

### VoidWeave

VoidWeave is a deinterlacing method involving in-painting with machine-learning.

It takes footage and separates the weaved fields so that each field is full-height with the missing data of the field
being 255 RGB green instead of empty/black. The in-painting machine-learning system would then in-paint the missing
data wherever it finds the 255 RGB Green pixels. It works quite well as YUV 4:2:0 DVD data doesn't seem to ever reach
255 green though it does get close, but never quite 255.

I tested it on a Live Action DVD and the results were honestly outstanding! The time it took to run the in-painting
was about the same as QTGMC on Very Slow, with similar results! I think where this method may really shine is with
Cartoon/Animated sources as QTGMC does not do them well.

It all still requires a lot more testing, but it looks like it could be a really nice method! Especially now that I've
learned Disney has also been working on it around the same tim, back in 2020 :P

## License

© 2020-2023 rlaphoenix — [GNU General Public License, Version 3.0](LICENSE)
