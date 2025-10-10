import os
from setuptools import setup

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

import fftools

setup(
    name='fftools',
    version=fftools.__version__,
    packages=["fftools"],
    include_package_data=True,
    description='A set of graphical tools built upon FFmpeg and other graphics libraries',
    long_description=README,
    url='https://chalier.fr/',
    author=fftools.__author__,
    author_email=fftools.__email__,
    install_requires=[
        "numpy",
        "Pillow",
        "tqdm",
        "opencv-python",
        "python-dateutil",
        "av",
    ],
)