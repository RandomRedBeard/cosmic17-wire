import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

import logging
from cosmic17.wire import value

logging.basicConfig(level=logging.DEBUG)

class foo:

    def __init__(self):
        self.__bar = None

    @value('path.to.bar')
    def bar(self):
        return self.__bar

    @bar.setter
    def bar(self, bar):
        self.__bar = bar

@value.set_parser
def parser(path: str):
    return 'ok'

value.wire_all()

if __name__ == "__main__":
    f = foo()

    assert f.bar == 'ok'