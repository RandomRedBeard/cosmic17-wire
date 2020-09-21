import inspect
import logging
from types import ModuleType
from typing import Callable, Any, List
from collections import defaultdict, OrderedDict

logger = logging.getLogger(__name__)

def default_parser(path: str) -> None:
    """
    Default parser does nothing.

    Args:
        path (str): [description]

    Returns:
        [type]: [description]
    """

    return None

class value(property):

    """
    Decorator class for defining an external path location
    for some variable.

    Resulting behavior similar to @property

    Ex. Setter injection

        class x:

            def __init__(self):
                self.__variable = None

            @value('path.to.var')
            def variable(self):
                return self.__variable

            @variable.setter
            def variable(self, variable):
                self.__variable = variable

        @value.set_parser
        def parser(path: str):
            '''Some lookup based on path'''
            return config[path]

    Ex2. Constructor injection

        class y:

            def __init__(self, foo):
                self.__foo = foo

            @value('path.to.foo')
            def foo(self):
                return self.__foo

    Ex3. Function injection

        GLOBAL_VAL = None

        @value('path.to.global_val')
        def set_global_val(global_val):
            global GLOBAL_VAL
            GLOBAL_VAL = global_val
    
    """

    _to_wire = list()
    parser: Callable[[str], Any] = default_parser

    def __init__(self, path):
        self.path = path

    def __rcall__(self, func):

        """
        Initial __call__ method.

        __rcall__ is meant to be reset after wiring is complete.

        Getter criteria: No parameters aside from 'self' and 'cls'

        Setter criteria: Only one parameter aside from 'self' and 'cls'

        Args:
            func (Callable): Either a getter or setter type function.

        Returns:
            value
        """

        parameters = inspect.signature(func).parameters.copy()

        # Ignore naming conventions of 'self' and 'cls'
        # If you don't follow these rules, maybe don't use this
        if 'self' in parameters:
            parameters.pop('self')

        if 'cls' in parameters:
            parameters.pop('cls')

        # We're gonna guess this is a getter
        lp = len(parameters)
        if lp == 0:
            super().__init__(func, self.fset, self.fdel)
        # And this is a setter
        elif lp == 1:
            super().__init__(self.fget, func, self.fdel)
        # And this is unknown
        else:
            raise AttributeError

        # We need to register this with _to_wire
        self._to_wire.append(self)

        return self

    def __call__(self, *args, **kwargs):
        """
        Callable cannot be changed by self.__call__ = x

        So we change the call under the covers through an intermediary method.

        """
        return self.__rcall__(*args, **kwargs)

    def setter(self, fset):
        super().__init__(self.fget, fset, self.fdel)
        return self

    def getter(self, fget):
        super().__init__(fget, self.fset, self.fdel)
        return self

    def deleter(self, fdel):
        super().__init__(self.fget, self.fset, fdel)
        return self

    class _mapping:

        """
        Internal class for defining a new __init__ per class.

        Args:
            cls__init__ (Callable): Original cls.__init__ for a given cls.
            values (List[value]): A list of injectable values for a given cls.
        """

        def __init__(self, cls__init__, values):
            self.cls__init__ = cls__init__
            self.values = values

        def new_init(self):
            """
            Creates a new __init__ for a given cls.

            Returns:
                Callable: New __init__
            """
            # Store instance variables in local scope for function
            cls__init__ = self.cls__init__
            values = self.values

            # Define a new init for each class
            def new__init__(self, *args, **kwargs):
                signature = inspect.signature(cls__init__)

                # Gives us a list of arguments that we can check off the list as
                # they we're likely overridden
                # Update: If we can't bind, we assume the user want's some constructor injected values.
                # We will add kwargs we can and let cls__init__ fail.
                # Update: Move to bind_partial and let cls__init__ fail.
                arguments = signature.bind_partial(self, *args, **kwargs).arguments

                # Attempting constructor injection
                # Setup attr map
                attr_map = {}
                value_: value
                for value_ in values:
                    # One of these functions exists to get here
                    checker = value_.fget if value_.fget else value_.fset
                    attr_map[checker.__name__] = value_

                logger.debug(f"Attr map {attr_map}")

                # Constructor injection
                for param in signature.parameters:
                    logger.debug(f"Param {param}")
                    
                    # I prefer negative case continues
                    if param not in attr_map or param in arguments:
                        continue

                    logger.debug(f"Attempting constructor injection {param}")
                    try:
                        # Get value from parser path
                        val = value.parser(value_.path)
                        
                        # Update kwargs
                        kwargs[param] = val

                        # Update arguments map to prevent double injection
                        arguments[param] = val
                    except:
                        logger.debug(f"Failed to inject {value_.path} via constructor", exc_info=True)

                cls__init__(self, *args, **kwargs)

                # Setter injection
                for value_ in values:
                    if value_.fset is None:
                        logger.debug(f"No setter found for {value_} path {value_.path}")
                        continue
                    
                    attr = value_.fset.__name__

                    if attr in arguments:
                        logger.debug(f"Skipping {attr} (provided)")
                        continue

                    logger.debug(f"Attempting setter injection {attr}")

                    try:
                        val = value.parser(value_.path)
                        value_.fset(self, val)
                    except Exception as e:
                        logger.debug(f"Setter injection failed {value_.fset} for path {value_.path}")

            return new__init__

    @staticmethod
    def walk_namespace(cns: ModuleType, namespaces: List[str]):
        """
        Finds tail namespace object for a list of str namespaces

        Args:
            cns (module): Root module for namespace traversal.
            namespaces (List[str]): List of namespaces to an object.

        Raises:
            ModuleNotFoundError: If namespaces path is invalid.

        Returns:
            module or type: Some namespace.
        """
        for namespace in namespaces:
            core = cns.__dict__
            if namespace in core:
                cns = core[namespace]
            else:
                raise ModuleNotFoundError

        return cns

    @classmethod
    def wire_all(cls):
        """
        Performs attribute injection for all collected value objects.

        Raises:
            AttributeError: If the __qualname__ of a given function cannot be used to trace
            back to that function.
        """
        # Map each cls with values to wire
        cls_map = defaultdict(list)

        value_: cls = None
        for value_ in cls._to_wire:
            checker = value_.fset if value_.fset else value_.fget
            module = inspect.getmodule(checker)

            # Traverse namespaces
            namespaces = checker.__qualname__.split('.')[:-1]
            try:
                cns = value.walk_namespace(module, namespaces)
            except ModuleNotFoundError:
                continue

            logger.debug(f"Found namespace {cns}")

            # CNS is now the namespace containing checker
            # Class case
            if isinstance(cns, type):
                cls_map[cns].append(value_)
            # A globally scoped module function (hopeful)
            elif isinstance(cns, ModuleType):
                if value_.fset:
                    # Use setter (Some function under the covers)
                    value_.fset(cls.parser(value_.path))

                    # Reset rcall on value side for fset
                    # This makes the function callable again
                    value_.__rcall__ = value_.fset
                else:
                    logger.debug(f"No setter found for {checker} {value_.path}")
            else:
                raise AttributeError(f"I think you are doing funny stuff {cns}")

        # Class variable injection
        for cls_, values in cls_map.items():
            logger.debug(f"Creating new __init__ for {cls_}")
            mp = cls._mapping(cls_.__init__, values)
            cls_.__init__ = mp.new_init()

    @classmethod
    def set_parser(cls, parser: Callable):
        """
        Sets value.parser.

        Args:
            parser (Callable): [description]

        Returns:
            [type]: parser
        """
        cls.parser = parser
        return parser