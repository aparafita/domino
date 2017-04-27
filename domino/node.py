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


    @property
    def state(self):
        return self._state


    @state.setter
    def state(self, value):
        self._state = value

        if self._state != Node.State.FINISHED and hasattr(self, '_result'):
            del self._result


    def reset_errors(self):
        """
            Reset state to IDLE to this node and all its sources 
            and the sources of those sources.
        """

        to_idle = { self }
        idled = set()

        while to_idle:
            node = to_idle.pop()
            node.state = Node.State.IDLE

            if '@domino.traceback' in node.variables:
                del node.variables['@domino.traceback']
            idled.add(node)

            for source in node.sources:
                if source not in idled:
                    to_idle.add(source)


    @property
    def result(self):
        if hasattr(self, '_result'):
            return self._result
        else:
            self.state = Node.State.IDLE
            return self.run()


    @result.setter
    def result(self, value):
        self._result = value


    def __call__(self):
        func, args, kwargs = self.item

        args = [
            deepcopy(arg.result) if isinstance(arg, Node) else arg
            for arg in args
        ]

        # Add self to args if func is bound
        if bound.is_bound(func):
            args = [ self ] + args

        kwargs = {
            k: deepcopy(v.result) if isinstance(v, Node) else v
            for k, v in kwargs.items()
        }

        self.result = func(*args, **kwargs)
        return self.result


    def run(self, filename=None, load=True, save_wait=10):
        """ Method used to run this node as the root of a DAG """

        # Try loading the tree before starting
        if filename is not None and load:
            self.load(filename)

        # Restart all sources of a node that had an error
        in_self = set(self) # preprocess it to save time
        for node in in_self:
            if node.state == Node.State.ERROR:
                node.reset_errors()
            elif node.state != Node.State.FINISHED:
                node.state = Node.State.IDLE
        
        # def queue(node):
        #     if node.state == Node.State.IDLE and all(
        #         target.state == Node.State.FINISHED 
        #         for target in node.targets
        #     ):
        #         yield node

        #     else:
        #         for target in node.targets:
        #             for node2 in queue(target):
        #                 yield node2

        # execution_queue = set(queue(self))
        execution_queue = {
            node
            for node in set(self)
            if node.state == Node.State.IDLE and all(
                target.state == Node.State.FINISHED 
                for target in node.targets
            )
        }
        wait_queue = set()

        processed_nodes = 0
        try:
            while execution_queue or wait_queue:
                while execution_queue:
                    node = execution_queue.pop()

                    try:
                        if not node.silent:
                            print('START: '.ljust(9) + node.name)

                        node.state = Node.State.RUNNING
                        node() # run its function
                        node.state = Node.State.FINISHED

                        if not node.silent:
                            print('END: '.ljust(9) + node.name)
                    except KeyboardInterrupt:
                        raise # don't catch this exception
                    except Sleep as e:
                        node.state = Node.State.DELAYED
                        wait_queue.add((node, e))

                        if not node.silent:
                            print('DELAYED: '.ljust(9) + node.name)

                        continue
                    except Exception as e:
                        node.state = Node.State.ERROR

                        # Save traceback in variables to check later
                        s = StringIO()
                        print_exc(file=s)
                        node.variables['@domino.traceback'] = s.getvalue()

                        if not node.silent:
                            print('ERROR: '.ljust(9) + node.name)

                        continue

                    for source in node.sources:
                        # Execute only nodes that self does depend on
                        if source in in_self: 
                            # for node in queue(source):
                            #     execution_queue.add(node)
                            execution_queue.update(
                                {
                                    node
                                    
                                    for node in set(source)
                                    if node.state == Node.State.IDLE and all(
                                        target.state == Node.State.FINISHED 
                                        for target in node.targets
                                    )
                                }
                            )

                    processed_nodes += 1

                    if filename is not None and processed_nodes == save_wait:
                        self.save(filename)
                        processed_nodes = 0

                while wait_queue:
                    wait_queue = {
                        (node, sleep)
                        for node, sleep in wait_queue
                        if (sleep.remaining() > 0) or execution_queue.add(node)
                        # notice that if we get to the add, 
                        # the if will be False because add returns None
                    }

                    if execution_queue:
                        break # something to execute, so don't sleep more
                    else:
                        node, sleep = min(wait_queue, key=lambda pair: pair[1])
                        sleep()

        except KeyboardInterrupt:
            if filename is not None:
                self.save(filename)
            raise

        if filename is not None:
            self.save(filename)

        if self.state == Node.State.FINISHED:
            #print(self)
            return self.result
        else:
            raise Exception('Tree finished with errors')


    def reset(self, state=State.IDLE):
        if hasattr(self, '_result'):
            del self._result

        if state is not None:
            self.state = state


    def save(self, filename):
        """
            Saves the current state of the graph 
            taking this node as the root in the selected file.
        """

        l = []
        saved_nodes = set()

        for node in self:
            if node in saved_nodes: continue

            d = {
                'name': node.name,
                'state': node.state,
                'variables': node.variables   
            }

            if node.store_result and hasattr(node, '_result'):
                d['result'] = node.result

            l.append(d)
            saved_nodes.add(node)

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
        loaded_nodes = set()

        if len(nodes) != len(l):
            raise Exception('Loaded tree doesn\'t match given tree')

        for node, node_d in zip(nodes, l):
            if node in loaded_nodes: continue

            if node.name != node_d['name']:
                raise Exception(
                    'Loaded tree definition doesn\'t match given tree'
                )

            node.state = node_d['state']
            node.variables = node_d['variables']

            if 'result' in node_d:
                node.result = node_d['result']

            loaded_nodes.add(node)


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
            node.state = Node.State.IDLE

        self.state = Node.State.IDLE