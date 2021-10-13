# Release History

## 4.2.0

- Add new `recover()` method to PD2V for recovering progressive frames with VFM optimally
- Support VFM recovered input clips in PD2V `deinterlace()`

## 4.1.0

- Update pyd2v to 1.3.0, remove PD2V._get_d2v
- Remove explicit VapourSynth dependency (prevents annoying conflicts between vs users who are on non-pip-installs vs. those on pip-installs)
- Rework release-packager workflow for releases

## 4.0.3

- Fix pathlib usage in `PD2V._get_d2v` and `PLWI._fps_reset`, stem and suffix was mixed up.

## 4.0.2

- Fix `__ALL__` imports in `__init__`, was using old PLS name after it was renamed to PLWI.

### PLWI

- State "Progressive" instead of "Deinterlaced (Progressive)" in deinterlace()'s verbose info.

## 4.0.1

- Create HISTORY.md
- Highly update the README with up-to-date information.
- Rename the new class PLS to PLWI.
- General improvements.

### PD2V

- Ensure deinterlace() kernel has no positional arguments set, and clip is a VideoNode.

## 4.0.0

New classes: PD2V, PLS, and, PKernel.
Removed classes: PSourcer, PDeinterlacer.

PD2V and PLS are derivatives from PSourcer and PDeinterlacer code. They work a lot differently too. The idea with the
new classes is to be specific for a codec/indexer format with specific functions for specific purposes that can be
used as needed. Each class method returns back the class instance so you can keep calling new methods on other methods
(one-line approach) until you ask for the `clip` of the class instance. This method makes using the classes very
convenient!

The main reason for this change has been to consolidate the code to their respective use-case. It's been a nightmare
to have one class deal with code for every codec, this way it allows me to manage only the code for the codec/indexer
that the class is for, much better!

- Added mypy configuration.
- Moved from setuptools to poetry for a much better package management experience.
- Update pyd2v requirements to 1.2.0 to take advantage of it's new load() method and other fixes.
- Properly handle the __ALL__ short hand imports for the classes in `__init__.py`. Including missing imports!
- Various improvements all over the README including fixes to typos, improving the information, removing unnecessary
  information, etc.

### PSourcer

- PSourcer has been removed entirely and split off into two classes. PD2V for MPEG-1/2 videos, and PLS for AVC (H.264) videos. Changes mentioned below have been accompanied to their associated new class but were changed as part of PSourcer originally.
- Image/imwri usage has been removed. There's no new class where that code is split off too. Images are simply no longer supported.
- Functions in the helper file that PSourcer has used, have been removed if it wasn't used elsewhere.
- change_chroma_loc has been removed, it isnt needed. If you really wanted to change the chroma loc, you could do it manually with a one-liner core.resize call.

### PDeinterlacer

- Like PSourcer, PDeinterlacer has had its close split off into PD2V and PLS where appropriate.
- Image/imwri usage has been removed. There's no new class where that code is split off too. Images are simply no longer supported.
- Functions in the helper file that PDeinterlacer has used, have been removed if it wasn't used elsewhere.

### PSourcer changes that made its way to PD2V

- core.d2v plugin will now be checked to ensure it's available.
- Fix decimation-based fps matching. It crashed when trying to apply the changes to the flags due to an incorrect flag enumeration.
- `debug` option has been changed to `verbose`. The info provided by verbose has changed. Some data is now split off to be applied during `__init__` and some during the `deinterlace()` call.
- Improve accuracy of the pulldown cycle calculation by checking each RFF group section separately from one another, and then choosing the most common computed cycle. This fixes accuracy issues that may occur when there are lots and lots of short sparse sections between interlaced sections.
- Pulldown calculation will no longer panic if no pulldown is used on the source.
- fps_divisor argument is no longer needed, all computations for it have been automated.

### PKernel

- New class which is just storage for any kind of custom deinterlacing kernel stuff I am working on that you may want to use.
- VoidWeave has been moved from PDeinterlacer to PKernel.

### helpers

- All D2V and LWI specific code has been moved to their respective new classes.
- Removed anti_file_prefix, file paths are now expected to be pathlib Path objects.
- Removed gcd, replaced all uses of it with math.gcd.
- Added get_standard function to convert an aspect float to a standard string.

## Older versions have generally no recorded change log
