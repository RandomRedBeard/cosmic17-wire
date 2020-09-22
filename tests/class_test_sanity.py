import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

import logging
from cosmic17.wire import Value

logging.basicConfig(level=logging.DEBUG)

class foo:

    def __init__(self, i):
        self.__bar = None
        self.__i = i

    @Value('path.to.bar')
    def bar(self):
        return self.__bar

    @bar.setter
    def bar(self, bar):
        self.__bar = bar

    @Value('path.to.i')
    def i(self):
        return self.__i

@Value.set_parser
def parser(path: str):
    return 'ok'

Value.wire_all()

if __name__ == "__main__":
    f = foo()

    print(f.__dict__)

    assert f.bar == 'ok'
    assert f.i == 'ok'