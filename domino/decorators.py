# Author: Álvaro Parafita (parafita.alvaro@gmail.com)

import inspect
from functools import wraps

def bound(func):
    """
        Decorator that identifies a function as bound for a domino Graph.
        That means that the first parameter of the decorated function
        will be the node that contains it.
    """

    func.__bound__ = True
    return func

bound.is_bound = lambda func: getattr(func, '__bound__', False)


def domino(name, node_class=None):
    """
        Decorator to create a Node creator based on a function.

        Example:

        @domino('f.{x}.{a}')
        def f(x, a=1):
            pass

        node = f(1, a=2)

        is the same as

        def f(x, a=1):
            pass

        f = Node('f.1.2', f, 1, a=2)
    """

    # This is done like this to avoid circular imports
    from .node import Node

    if node_class is None:
        node_class = Node

    def dec(func):
        arg_names = inspect.getfullargspec(func).args
        if bound.is_bound(func):
            arg_names = arg_names[1:]

        @wraps(func)
        def f(*args, **kwargs):
            format = {
                k: args[n]
                for n, k in enumerate(arg_names)
                if n < len(args)
            }

            format.update(kwargs)

            format = {
                k: v.name if isinstance(v, Node) else v
                for k, v in format.items()
            }

            return node_class(
                name.format(**format), 
                func, 
                *args, 
                **kwargs
            )

        return f

    return dec