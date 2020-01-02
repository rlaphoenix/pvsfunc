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
`from pvsfunc.mpeghelper import MpegHelper`
`MpegHelper(file_path[, bool rff=True, bool debug=False])`
* file_path: Path to a file to import as a clip. For MPEG (versions 1 and 2) it's best to use a d2v file.
* rff: Repeated Fields First. It's essentially a toggle switch for Pulldown. Only set this to false if you are sure it's entirely FILM or you don't want the non-FILM frames. In mostly FILM content, the non-FILM frames are typically post-production frames, like transition's and such.
* debug: Debug Mode. This will give you a new GUI process with a text box, this text box will write debugging information on use. It may also print data to the frame itself via `core.text.Text`.