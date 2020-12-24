#!/bin/bash

rm -r build
rm -r dist
rm -r "pvsfunc.egg-info"
python setup.py sdist bdist_wheel
sudo python -m pip install .