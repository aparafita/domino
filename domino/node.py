# Author: Álvaro Parafita (parafita.alvaro@gmail.com)

from functools import total_ordering
from traceback import print_exc
from io import StringIO
from copy import deepcopy

import os.path

import time
from datetime import datetime, timedelta

import json

from .dag import DAGNode
from .decorators import bound


@total_ordering
class Sleep(Exception):
    """
        Special exception that can be raised by a Node function.
        It delays the reexecution of a node 
        for the number of seconds it states.
    """

    NOTIFY_AT = 10

    def __init__(self, seconds):
        self.end = datetime.now() + timedelta(seconds=seconds)


    def remaining(self):
        return (self.end - datetime.now()).total_seconds()


    def __call__(self):
        try:
            sleep = time.sleep # Unix
        except AttributeError:
            sleep = time.wait # Windows

        rem = self.remaining()

        # only notify if the wait takes longer that NOTIFY_AT seconds
        if self.NOTIFY_AT >= 0 and rem >= self.NOTIFY_AT: 
            print('Asleep for %.2f seconds. Waking up at %s' % (rem, self.end))

        if rem > 0:
            sleep(rem)


    def __eq__(self, other): return self.end == other.end
    def __le__(self, other): return self.end <= other.end
    def __hash__(self): return hash(self.end)
    def __bool__(self): return self.remaining() > 0


class Node(DAGNode):
    """
        Main element of a domino graph.
        Each node contains a name, a function and its parameters.
        Each node can be added some targets, which will be the nodes
        it has to wait to finish in order to execute itself.

        Each node has also a run method that executes the graph
        taking this node as the root node.

        Node class also stores a subclass State, that contains
        all the different states a Node can be in.
    """

    silent = False

    class State:

        IDLE = 'idle'
        RUNNING = 'running'
        DELAYED = 'delayed'
        ERROR = 'error'
        FINISHED = 'finished'


    def __init__(self, name, func, *args, **kwargs):
        super().__init__((func, args, kwargs), name)

        # Add any node that appears in args or kwargs
        for arg in args:
            if isinstance(arg, Node):
                self.add(arg)

        for v in kwargs.values():
            if isinstance(v, Node):
                self.add(v)

        self.state = Node.State.IDLE
        self.variables = {}

        self.store_result = True
        self.sleep = None


    @property
    def state(self):
        return self._state


    @state.setter
    def state(self, value):
        self._state = value

        if self._state != Node.State.FINISHED and hasattr(self, '_result'):
            del self._result


    def reset(self):
        if hasattr(self, '_result'):
            del self._result

        self.state = Node.State.IDLE


    def set_function(self, func, reset=True):
        """
            Changes function for this node and resets it
        """
        oldfunc, args, kwargs = self.item

        if bound.is_bound(oldfunc) and not bound.is_bound(func):
            func = bound(func)

        self.item = (func, args, kwargs)
        if reset: self.reset()

        return self


    def reset_errors(self):
        """
            Reset state to IDLE to this node and all its sources 
            and the sources of those sources.
        """

        to_idle = { self }
        queued = { self }

        while to_idle:
            node = to_idle.pop()
            node.state = Node.State.IDLE

            if '@domino.traceback' in node.variables:
                del node.variables['@domino.traceback']
            
            for source in node.sources:
                if source not in queued:
                    to_idle.add(source)
                    queued.add(source)


    @property
    def result(self):
        if hasattr(self, '_result'):
            result = self._result
        else:
            self.state = Node.State.IDLE
            result = self.run()

        return deepcopy(result)


    @result.setter
    def result(self, value):
        self._result = value


    def save(self, filename):
        """
            Saves the current state of the graph 
            taking this node as the root in the selected file.
        """

        l = []

        for node in self:
            d = {
                'name': node.name,
                'state': node.state,
                'variables': node.variables   
            }

            if node.store_result and hasattr(node, '_result'):
                d['result'] = node.result

            l.append(d)

        j = json.dumps(l, indent=2)

        with open(filename, 'w') as f:
            f.write(j)


    def load(self, filename):
        try:
            with open(filename) as f:
                l = json.loads(f.read())
        except FileNotFoundError:
            return

        nodes = list(self)

        if len(nodes) != len(l):
            raise Exception('Loaded tree doesn\'t match given tree')

        for node, node_d in zip(nodes, l):
            if node.name != node_d['name']:
                raise Exception(
                    'Loaded tree definition doesn\'t match given tree'
                )

            node.state = node_d['state']
            node.variables = node_d['variables']

            if 'result' in node_d:
                node.result = node_d['result']


    def __call__(self):
        func, args, kwargs = self.item

        args = [
            arg.result if isinstance(arg, Node) else arg
            for arg in args
        ]

        # Add self to args if func is bound
        if bound.is_bound(func):
            args = [ self ] + args

        kwargs = {
            k: v.result if isinstance(v, Node) else v
            for k, v in kwargs.items()
        }

        self.result = func(*args, **kwargs)
        return self.result


    def run(self, filename=None, load=True, save_wait=10):
        """ Method used to run this node as the root of a DAG """

        # Try loading the tree before starting
        if filename and load:
            self.load(filename)

        # Reset errors and their sources
        for node in self:
            if node.state == Node.State.ERROR:
                node.reset_errors()

        # Reset non-finished nodes or OpNodes
        for node in self:
            if node.state != Node.State.FINISHED \
                or not hasattr(node, '_result'):
                node.state = Node.State.IDLE

        ready_to_run = lambda node: (
            not node.sleep and 
            node.state in (
                Node.State.IDLE, Node.State.DELAYED
            ) and all(
                target.state == Node.State.FINISHED
                for target in node.targets
            )
        )

        def run(node):
            if not node.silent:
                print('START: '.ljust(9) + node.name)

            node.state = Node.State.RUNNING
            node() # run its function
            node.state = Node.State.FINISHED

            if not node.silent:
                print('END: '.ljust(9) + node.name)


        # Let's start running
        iterations = 0
        executed = set() 
        asleep = set()
        current_node = self

        try:
            while self.state != Node.State.FINISHED:
                found = False # will be True when a node is run

                try:
                    stack = [ 
                        source for source in current_node.sources 
                    ] if current_node.sources else [ self ]
                    stacked = set(stack)

                    while stack:
                        node = stack.pop()

                        if ready_to_run(node):
                            run(node)
                            executed.add(node)

                            current_node = node
                            found = True
                            break
                        else:
                            for node in node.targets:
                                if node not in stacked and node not in executed:
                                    stack.append(node)
                                    stacked.add(node)

                    if found:
                        iterations += 1

                except Sleep as s:
                    print('DELAYED: '.ljust(9) + node.name)
                    node.sleep = s
                    node.state = Node.State.DELAYED
                    asleep.add(node)

                    # We'll continue with the previous current_node
                    continue 

                except Exception:
                    node.state = Node.State.ERROR

                    # Save traceback in variables to check later
                    s = StringIO()
                    print_exc(file=s)
                    node.variables['@domino.traceback'] = s.getvalue()

                    if not node.silent:
                        print('ERROR: '.ljust(9) + node.name)

                    if filename:
                        self.save(filename)

                    raise

                if not found:
                    if asleep:
                        # Some Nodes must be asleep 
                        # and they're the only ones that can run.                            
                        current_node = min(
                            asleep,
                            key=lambda node: node.sleep.remaining()
                        )

                        # sleep for what's necessary before proceeding
                        current_node.sleep()

                        asleep = {
                            node
                            for node in asleep
                            if node.sleep is not None and node.sleep.remaining()
                        }
                    else:
                        # We might have lost track after some sleeps. 
                        # Start searching from self again
                        current_node = self

                # Save whenever we execute save_wait nodes
                if filename and iterations and not iterations % save_wait:
                    self.save(filename)

        except KeyboardInterrupt:
            if filename: 
                self.save(filename)

            raise

        # Save at the end
        if filename:
            self.save(filename)

        return self.result


    def __iter__(self): 
        return self.yield_nodes(order=lambda node: node.name)

    def __hash__(self): return hash(self.item[0])


class OpNode(Node):

    """
        OpNode stands for OperationalNode.

        Special type of Node that is meant not to store 
        the result its function returns. 
        It just saves the result in memory and 
        it can be rerun every time it's needed
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.store_result = False


class Root(OpNode):
    """
        Special Node that only returns the results of the specified nodes.
        Used to contain several functions in a unique node 
        in order to run them with a same graph.
    """

    silent = True

    def __init__(self, name, *nodes):
        # Save all nodes that this root contains
        self.subnodes = {
            target
            for node in nodes
            for target in node
        }

        self.original_leaves = [
            target
            for node in nodes # cross the graph
            for target in node
            if not target.targets # is leaf
        ] + [ self ]

        super().__init__(
            name, 
            lambda *args: [ 
                arg 
                for node, arg in zip(nodes, args) 
                if node.store_result 
            ],
            *nodes
        )

        self.state = Node.State.IDLE
        self.variables = {}


    def add(self, target, as_root=False):
        if as_root:
            for original_leaf in self.original_leaves:
                if isinstance(original_leaf, Root):
                    original_leaf.add(target, as_root=original_leaf != self)
                else:
                    original_leaf.add(target)
        else:
            super().add(target)


    def rm(self, target, as_root=False):
        if as_root:
            for original_leaf in self.original_leaves:
                if isinstance(original_leaf, Root):
                    original_leaf.rm(target, as_root=original_leaf != self)
                else:
                    original_leaf.rm(target)
        else:
            super().rm(target)


    def reset(self):
        """
            Reset state to IDLE of all nodes that originally defined this Root
        """

        for node in self.subnodes:
            node.reset()

        super().reset()