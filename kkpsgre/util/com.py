import re, copy, datetime


__all__ = [
    "strfind",
    "check_type",
    "check_type_list",
    "check_str_is_integer",
    "check_str_is_float",
    "dict_override",
    "str_to_datetime",
    "find_matching_words",
]


def strfind(pattern: str, string: str, flags=0) -> bool:
    if len(re.findall(pattern, string, flags=flags)) > 0:
        return True
    else:
        return False

def check_type(instance: object, _type: object | list[object]):
    _type = [_type] if not (isinstance(_type, list) or isinstance(_type, tuple)) else _type
    is_check = [isinstance(instance, __type) for __type in _type]
    if sum(is_check) > 0:
        return True
    else:
        return False

def check_type_list(instances: list[object], _type: object | list[object], *args: object | list[object]):
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

def str_to_datetime(string: str, tzinfo: datetime.timezone=datetime.timezone.utc) -> datetime.datetime:
    def __work(str_datetime: str, strptime: str):
        try:
            date = datetime.datetime.strptime(str_datetime, strptime)
        except ValueError:
            return False, None
        return True, date
    boolwk, date = __work(string, "%Y-%m-%d %H:%M:%S.%f%z")
    if boolwk: return date
    boolwk, date = __work(string, "%Y-%m-%d %H:%M:%S.%f")
    if boolwk: return date
    boolwk, date = __work(string, "%Y-%m-%d %H:%M:%S%z")
    if boolwk: return date
    boolwk, date = __work(string, "%Y-%m-%d %H:%M:%S")
    if boolwk: return date
    boolwk, date = __work(string, "%Y/%m/%d %H:%M:%S.%f%z")
    if boolwk: return date
    boolwk, date = __work(string, "%Y/%m/%d %H:%M:%S.%f")
    if boolwk: return date
    boolwk, date = __work(string, "%Y/%m/%d %H:%M:%S%z")
    if boolwk: return date
    boolwk, date = __work(string, "%Y/%m/%d %H:%M:%S")
    if boolwk: return date
    boolwk, date = __work(string, "%Y-%m-%d%z")
    if boolwk: return date
    boolwk, date = __work(string, "%Y-%m-%d")
    if boolwk: return date
    boolwk, date = __work(string, "%Y/%m/%d%z")
    if boolwk: return date
    boolwk, date = __work(string, "%Y/%m/%d")
    if boolwk: return date
    if   strfind(r"^[0-9]+$", string) and len(string) == 8:
        return datetime.datetime(int(string[0:4]), int(string[4:6]), int(string[6:8]), tzinfo=tzinfo)
    elif strfind(r"^[0-9]+$", string) and len(string) == 14:
        return datetime.datetime(int(string[0:4]), int(string[4:6]), int(string[6:8]), int(string[8:10]), int(string[10:12]), int(string[12:14]), tzinfo=tzinfo)
    else:
        raise ValueError(f"{string} is not converted to datetime.")

def find_matching_words(string: str, start_words: str | list[str], end_words: str | list[str], is_case_inensitive: bool=False) -> (int, int):
    assert isinstance(string, str)
    assert isinstance(start_words, str) or (isinstance(start_words, list) and check_type_list(start_words, str))
    assert isinstance(end_words,   str) or (isinstance(end_words,   list) and check_type_list(end_words,   str))
    if isinstance(start_words, str): start_words = [start_words, ]
    if isinstance(end_words,   str): end_words   = [end_words,   ]
    if is_case_inensitive:
        string      = string.lower()
        start_words = [x.lower() for x in start_words]
        end_words   = [x.lower() for x in end_words  ]
    i_string = float("inf")
    for x in start_words:
        tmp = string.find(x)
        if 0 <= tmp and i_string > tmp:
            tmp      = tmp + len(x)
            i_string = tmp
    if i_string == float("inf"):
        i_string = -1
    else:
        string = string[i_string:]
    j_string = float("inf")
    for x in end_words:
        tmp = string.find(x)
        if 0 <= tmp and j_string > tmp:
            j_string = tmp
    if j_string == float("inf"):
        j_string = -1
    else:
        j_string = j_string + (i_string if i_string >= 0 else 0 )
    return i_string, j_string
