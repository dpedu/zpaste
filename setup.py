#!/usr/bin/env python3

from setuptools import setup
import os


__version__ = "0.0.0"
with open(os.path.join(os.path.dirname(__file__), "requirements.txt")) as f:
    __requirements__ = [line.strip() for line in f.readlines()]


setup(name='wastebin',
      version=__version__,
      description='lazy pastebin',
      url='',
      author='dpedu',
      author_email='dave@davepedu.com',
      packages=['wastebin'],
      install_requires=__requirements__,
      entry_points={
          "console_scripts": [
              "wastebind = wastebin.daemon:main",
              "wpaste = wastebin.cli:main"
          ]
      },
      zip_safe=False)
