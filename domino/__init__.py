# Author: Álvaro Parafita (parafita.alvaro@gmail.com)

__version__ = '0.1.3'

from .node import Node, Root, Sleep, OpNode
from .decorators import domino, bound

from .chain import chain, link
dc, dl = chain, link

from . import factory, utils