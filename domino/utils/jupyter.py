# Author: Álvaro Parafita (parafita.alvaro@gmail.com)

"""
    Utilities for Jupyter Notebooks
"""

# Add parent folder to path and change dir to it
# so that we can access easily to all code and data in that folder

import sys
import os
import os.path


def notebook_init(path=os.path.pardir):
    """
        Assuming a project is built in a root folder 
        with a notebooks subfolder where all .ipynb files are located,
        run this function as the first cell in a notebook 
        to make it think the current folder is the project folder,
        so all subfolders of the root folder are accessible directly.

        Also, any imports inside the root folder will be accessible too.
    """

    if os.path.split(os.path.abspath(os.path.curdir))[-1] == 'notebooks':
        sys.path.append(os.path.abspath(path))
        os.chdir(path)