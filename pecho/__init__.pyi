from typing import Any, Callable, Dict, List, TextIO

__all__: List[str]
__version__: str

def echo(
    *objects: Any,
    newline: bool = False,
    end: str = '',
    str_convert_func: Callable = str,
    print_func: Callable = print,
    _: Dict[str, str] = {},
    **print_kwargs: Any,
): ...
