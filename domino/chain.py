# Author: Álvaro Parafita (parafita.alvaro@gmail.com)

"""
    Module that contains utility functions chain and link.

    chain tries to mimick the magrittr %>% pipe from R.
    It is a function call where each result passes to the next function
    as their first argument. 

    One can use link in two ways:
        * As a way of currying some of the arguments for a function call:
            link(func, arg1, arg2, kwarg1=val1)
        * As a placeholder for the "previous" result. 
            If link appears as an argument of a function call, 
            then it will not be placed as the first argument of the call.
            It will just appear wherever link is placed.

    Finally, if a string is passed as a function to apply, 
    chain will read it as the method assigned to the previous result
    that has that name.

    Two abbreviatures are included: 
        * dc (which stands for domino chain)
        * dl (which stands for domino.link)
"""

class _Link:

    def __init__(self, func, *args, **kwargs):
        if type(func) is str:
            self.func = lambda prev, *args, **kwargs: \
                getattr(prev, func)(*args, **kwargs)

            self._prev_first = True

        else:
            self.func = func

            self._prev_first = all(
                arg is not _Link
                for arg in args
            ) and all(
                arg is not _Link
                for arg in kwargs.values()
            )
   
        self.args = args
        self.kwargs = kwargs


    def __call__(self, prev):
        # Replace '_Link' for prev in args and kwargs
        args = (
            prev if arg is _Link else arg
            for arg in self.args
        )

        kwargs = {
            key: prev if arg is _Link else arg
            for key, arg in self.kwargs.items()
        }

        if self._prev_first:
            return self.func(prev, *args, **kwargs)
        else:
            return self.func(*args, **kwargs)


def chain(obj, *funcs):
    for func in funcs:
        if type(func) is not _Link:
            func = _Link(func)

        obj = func(obj)

    return obj


# Aliases
link = _Link

dc = chain
dl = link


# Examples
# import pandas as pd
# np = pd.np

# from ggplot import *

# chain(
#     np.random.random(150).reshape((50, 3)),
#     link(pd.DataFrame, columns=['x', 'y', 'strength']),
#     'head',
#     link(ggplot, aes('x', 'y', color='strength'))
# ) + geom_point()

# dc(
#     {
#         'x': np.random.random(100),
#         'y': np.random.random(100),
#         'cls': np.random.choice(['a', 'b'], 100)
#     },
#     pd.DataFrame,
#     dl(ggplot, aes('x', 'y', color='cls'))
# ) + geom_point()