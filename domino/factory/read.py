# Author: Álvaro Parafita (parafita.alvaro@gmail.com)

from ..decorators import domino
from ..node import OpNode

@domino('read_gzip.{filename}', node_class=OpNode)
def read_gzip(
    filename, 
    limit=None, 
    decode=None, 
    apply=None, 
    file_wrapper=lambda f: f
):
    """
        Reads file with name 'filename',
        returning up until 'limit' rows, if given,
        using encoding 'decode',
        applying function 'apply' to every line, if given.
        
        A wrapper for the file can be used to read lines from it 
        (preferably an iterator).
    """
    
    import gzip
    
    def yield_lines(f):
        for n, line in enumerate(f):
            if limit is None or n < limit:
                yield line.decode(decode) if decode else line
            else:
                break
        
    with gzip.open(filename, 'rb') as f:
        if file_wrapper is not None:
            f = file_wrapper(yield_lines(f))
        
        return [
            apply(line) if apply else line
            for line in f
        ]