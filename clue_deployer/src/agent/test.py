from __future__ import print_function
from psc import FixedQueue, NodeUsage
from datetime import datetime
import random
import uuid

from sys import getsizeof, stderr,exit
from itertools import chain
from collections import deque
try:
    from reprlib import repr
except ImportError:
    pass

def _total_size(o, handlers={}, verbose=False):
    """ Returns the approximate memory footprint an object and all of its contents.

    Automatically finds the contents of the following builtin containers and
    their subclasses:  tuple, list, deque, dict, set and frozenset.
    To search other containers, add handlers to iterate over their contents:

        handlers = {SomeContainerClass: iter,
                    OtherContainerClass: OtherContainerClass.get_elements}

    """
    dict_handler = lambda d: chain.from_iterable(d.items())
    all_handlers = {tuple: iter,
                    list: iter,
                    deque: iter,
                    dict: dict_handler,
                    set: iter,
                    frozenset: iter,
                   }
    all_handlers.update(handlers)     # user handlers take precedence
    seen = set()                      # track which object id's have already been seen
    default_size = getsizeof(0)       # estimate sizeof object without __sizeof__

    def sizeof(o):
        if id(o) in seen:       # do not double count the same object
            return 0
        seen.add(id(o))
        s = getsizeof(o, default_size)

        if verbose:
            print(s, type(o), repr(o), file=stderr)

        for typ, handler in all_handlers.items():
            if isinstance(o, typ):
                s += sum(map(sizeof, handler(o)))
                break
        return s

    return sizeof(o)

def total_size(o):
    handlers = {
        NodeUsage: lambda n: chain.from_iterable(n.processes),
        FixedQueue: lambda q: q.elements()
    }
    return _total_size(o,handlers=handlers,verbose=False)

def test_fixed_queue(size=100, max_process=96):
    start = datetime.now()
    q = FixedQueue(size)
    for i in range(size):
        n = NodeUsage(str(i)) 
        n.timestamp = datetime.now()
        n.cpu_usage = random.random()
        n.memory_usage = random.randint(100,8000)
        n.network_usage = random.random()
        n.wattage = random.random()*100000
        for i in range(0,random.randint(1,max_process)):
            n.processes.append((str(uuid.uuid4()),random.random()))
        q.put(n)
    dur = datetime.now()-start
    print(f"{size},{max_process} took:\t {dur.total_seconds()}, size:\t {total_size(q)} bytes")

if __name__ == '__main__':
    test_fixed_queue()
    test_fixed_queue(1000)
    test_fixed_queue(1000,1000)
    test_fixed_queue(100000)
    exit(0)

        