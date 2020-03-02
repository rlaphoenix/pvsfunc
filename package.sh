sudo rm -r build
sudo rm -r dist
sudo rm -r "pvsfunc.egg-info"
python3 setup.py sdist bdist_wheel
python3 -m twine upload dist/*