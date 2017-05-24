# Author: Álvaro Parafita (parafita.alvaro@gmail.com)

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