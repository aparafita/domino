# Author: Álvaro Parafita (parafita.alvaro@gmail.com)

class DAGException(Exception):
    """
        Specific Exception that contains all errors 
        that come as a result of a DAG operation
    """

    def __init__(self, message, *nodes):
        self.message = message
        self.nodes = nodes

    def __str__(self):
        return 'DAG Exception invoving %s: \'%s\'' % (self.nodes, self.message)


class DAGNode:
    """
        Node of a Directed Acyclic Graph.
        Contains an item and a name to identify it.
        All nodes that come as a target of another node 
        must have unique names along those targets.
    """

    def __init__(self, item, name):
        self.item = item
        self.name = name

        self.targets = set()
        self.sources = set()


    def add(self, target):
        # Check that target hasn't been added yet
        if target in self.targets:
            return

        # Check that target.name is not picked up
        elif target.name in (node.name for node in self.targets):
            raise DAGException(
                'Repeated target name (%s)' % target.name, 
                self, 
                target
            )

        # Check that this addition does not produce any loops
        elif self in target:
            raise DAGException(
                'Cycle produced by addition (%s, %s)' % (
                    self.name, 
                    target.name
                ),
                self, 
                target
            )

        # Finally, add the target
        self.targets.add(target)
        target.sources.add(self)


    def rm(self, target):
        if target in self.targets:
            self.targets.remove(target)
            target.sources.remove(self)

        else:
            raise DAGException(
                'Target not in node.targets (%s)' % target.name,
                self,
                target
            )


    def yield_nodes(self, order=None):
        to_yield = [ self ]
        yielded = set()

        while to_yield:
            node = to_yield.pop(0)

            yield node
            yielded.add(node)

            if order:
                targets = sorted(node.targets, key=order)
            else:
                targets = node.targets

            for target in targets:
                if target not in yielded:
                    to_yield.append(target)


    def __getitem__(self, key):
        if type(key) == str:
            for target in self.targets:
                if target.name == key:
                    return target
            else:
                raise KeyError(key)
        elif type(key) in (int, slice):
            targets = sorted(self.targets, key=lambda x: x.name)
            return targets[key]
        else:
            raise TypeError(key)


    def __iter__(self):
        return self.yield_nodes()


    def __str__(self): return '<Node %s>' % self.name
    def __repr__(self): return str(self)
    def __hash__(self): return hash(self.item)