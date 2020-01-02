from setuptools import setup, find_packages

with open("README.md", "r") as f:
    readme = f.read()

setup(
    name="pvsfunc",
    version="1.0.0",
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
        "pymediainfo"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GPLv3 License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)