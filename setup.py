from setuptools import setup, find_packages

with open("README.md", "r") as f:
    readme = f.read()

setup(
    name="pvsfunc",
    version="3.3.2",
    author="PHOENiX",
    author_email="pragma.exe@gmail.com",
    description="PHOENiX's compilation of VapourSynth Script's and Functions",
    license="GPLv3",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/rlaPHOENiX/pvsfunc",
    packages=find_packages(),
    install_requires=[
        "vapoursynth",
        "pymediainfo",
        "pyd2v>=1.0.4"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)
