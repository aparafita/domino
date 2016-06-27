# -*- coding: utf-8 -*-
# Author: Álvaro Parafita (parafita.alvaro@gmail.com)

from distutils.core import setup

import domino

setup(
    name = "domino",
    packages = ["domino"],
    version = domino.__version__,
    description = "Library to structure processes",
    author = "Álvaro Parafita",
    author_email = "parafita.alvaro@gmail.com",
    keywords = ["etl", "processing"],
    classifiers = [
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Development Status :: 4 - Beta",
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
        #"License :: 
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        #"Topic :: 
        ],
    long_description = """\
Library to structure processes
-------------------------------------

This version requires Python 3; no Python 2 version is available.
"""
)