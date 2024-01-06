import re, copy
from typing import List, Union


__all__ = [
    "strfind",
    "check_type",
    "check_type_list",
    "check_str_is_integer",
    "check_str_is_float",
]


def strfind(pattern: str, string: str, flags=0) -> bool:
    if len(re.findall(pattern, string, flags=flags)) > 0:
        return True
    else:
        return False

def check_type(instance: object, _type: Union[object, List[object]]):
    _type = [_type] if not (isinstance(_type, list) or isinstance(_type, tuple)) else _type
    is_check = [isinstance(instance, __type) for __type in _type]
    if sum(is_check) > 0:
        return True
    else:
        return False

def check_type_list(instances: List[object], _type: Union[object, List[object]], *args: Union[object, List[object]]):
    """
    Usage::
        >>> check_type_list([1,2,3,4], int)
        True
        >>> check_type_list([1,2,3,[4,5]], int, int)
        True
        >>> check_type_list([1,2,3,[4,5,6.0]], int, int)
        False
        >>> check_type_list([1,2,3,[4,5,6.0]], int, [int,float])
        True
    """
    if isinstance(instances, list) or isinstance(instances, tuple):
        for instance in instances:
            if len(args) > 0 and isinstance(instance, list):
                is_check = check_type_list(instance, *args)
            else:
                is_check = check_type(instance, _type)
            if is_check == False: return False
        return True
    else:
        return check_type(instances, _type)

def check_str_is_integer(string: str):
    boolwk = strfind(r"^[0-9]$", string) or strfind(r"^-[1-9]$", string) or \
             strfind(r"^[0-9]\.0+$", string) or strfind(r"^-[1-9]\.0+$", string) or \
             strfind(r"^[1-9][0-9]+$", string) or strfind(r"^-[1-9][0-9]+$", string) or \
             strfind(r"^[1-9][0-9]+\.0+$", string) or strfind(r"^-[1-9][0-9]+\.0+$", string)
    boolwk = boolwk & (string.zfill(len("9223372036854775807")) <= "9223372036854775807") # Is not integer over int64.
    return boolwk

def check_str_is_float(string: str):
    boolwk = strfind(r"^[0-9]\.[0-9]+$", string) or strfind(r"^-[0-9]\.[0-9]+$", string) or \
             strfind(r"^[1-9][0-9]+\.[0-9]+$", string) or strfind(r"^-[1-9][0-9]+\.[0-9]+$", string)
    return boolwk

def dict_override(_base: dict, _target: dict):
    """
    Usage::
        >>> x = {"a": 1, "b": 2, "c": [1,2,3],   "d": {"a": 2, "b": {"aa": 2, "bb": [2,3]}, "c": [1,2,3]}}
        >>> y = {        "b": 3, "c": [1,2,3,4], "d": {        "b": {"bb": [1,2,3]       }, "c": "aaa"  }}
        >>> dict_override(x, y)
    """
    base   = copy.deepcopy(_base)
    target = copy.deepcopy(_target)
    def work(a, b):
        for x, y in b.items():
            if isinstance(y, dict):
                work(a[x], y)
            else:
                a[x] = y
    work(base, target)
    return base