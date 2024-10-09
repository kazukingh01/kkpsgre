import re, datetime, copy
import pandas as pd
import numpy as np
# local package
from kkpsgre.util.com import check_type, check_type_list, str_to_datetime


__all__ = [
    "escape_mysql_reserved_word",
    "to_str_timestamp",
    "parse_conditions",
    "sql_to_mongo_filter",
]


OPERATORS_MONGO = {
    "=": "$eq",
    "!=": "$ne",
    "<>": "$ne",
    "<": "$lt",
    "<=": "$lte",
    ">": "$gt",
    ">=": "$gte",
    "AND": "$and",
    "and": "$and",
    "OR": "$or",
    "or": "$or",
    "IN": "$in",
    "in": "$in",
}
DICT_CONV_MONGO = {
    "true":  True, 
    "false": False, 
    "True":  True, 
    "False": False, 
}


def escape_mysql_reserved_word(sql: str, reserved_word: list[str]):
    assert isinstance(sql, str)
    assert isinstance(reserved_word, list) and check_type_list(reserved_word, str)
    sqls = []
    for tmp1 in sql.split("("):
        sqls.append([])
        for tmp2 in tmp1.split(")"):
            sqls[-1].append([])
            for tmp3 in tmp2.split(","):
                tmp4 = " ".join([f"`{x}`" if x in reserved_word else x for x in tmp3.split(" ")])
                sqls[-1][-1].append(tmp4)
    sqlnew = []
    for tmp1 in sqls:
        sqlnew.append([])
        for tmp2 in tmp1:
            sqlnew[-1].append(",".join(tmp2))
    sqlnew = [")".join(x) for x in sqlnew]
    sqlnew = "(".join(sqlnew)
    return sqlnew
    
def parse_conditions(sql_where_clause):
    def __tmp(tmp):
        try:
            return str_to_datetime(tmp)
        except ValueError:
            return tmp
    def __work(value):
        if value in DICT_CONV_MONGO:
            return DICT_CONV_MONGO[value]
        else:
            value = eval(value)
            if isinstance(value, str):
                return __tmp(value)
            elif isinstance(value, tuple) or isinstance(value, list):
                return [(__tmp(x) if isinstance(x, str) else x) for x in value]
            else:
                return value
    pattern = r"(\w+)\s*(\sIN\s|!=|<>|<=|>=|<|>|=)\s*('[^']*'|\w+|\(.*\))(\s+AND|\s+OR|\s*$)"
    matches = re.findall(pattern, sql_where_clause, re.IGNORECASE)
    current_operator   = None
    current_conditions = []
    mongo_query        = {}
    for match in matches:
        field, operator, value, logical_op = [x.strip() for x in match] # ex) field: aa, operator: >, value: 0, logical_op: and
        condition = {field: {OPERATORS_MONGO[operator]: __work(value)}}
        if logical_op:
            if current_operator and current_operator != OPERATORS_MONGO[logical_op]:
                mongo_query[current_operator] = current_conditions
                current_conditions = []
            current_operator = OPERATORS_MONGO[logical_op]
        current_conditions.append(condition)
    if current_operator:
        mongo_query[current_operator] = current_conditions
    else:
        mongo_query = current_conditions[0]
    return mongo_query

def sql_to_mongo_filter(sql_where_clause):
    """
    sql_where_clause = '''
    gender in ('male', 'female', 0) and ((name = 'Taro'))
    and (
        (department = 'Sales' AND age > 30) 
        OR 
        (department = 'Engineering' AND (salary > 70000 OR position IN ('Manager', 'Lead Engineer')))
    )
    AND 
    (location = 'New York' OR location = 'San Francisco')
    '''.strip()
    """
    sql_where_clause  = re.sub(r"\s+", " ", sql_where_clause).strip().replace(" AND ", " and ").replace(" And ", " and ").replace(" OR ", " or ").replace(" Or ", " or ")
    def __work1(string: str):
        listret, count, st_i = [], None, 0        
        for i, word in enumerate(string):
            if word == "(":
                if count is None:
                    listret.append(string[st_i:i])
                    count = 1
                    st_i  = i
                else:
                    count += 1
            if word == ")":
                if count is None:
                    raise ValueError(f"Strange input: {string}")
                else:
                    count -= 1
            if count is not None and count == 0:
                listret.append(string[st_i:i+1])
                count = None
                st_i  = i+1
        listret.append(string[st_i:])
        listret = [x for x in listret if x.strip() != ""]
        listretwk = [listret[0], ]
        for x in listret[1:]:
            if x.find(" and ") >= 0 or x.find(" or ") >= 0:
                listretwk.append(x)
            else:
                # a case of IN phrase is expected.
                listretwk[-1] = listretwk[-1] + x
        listret = listretwk
        listret = [x for x in listret if x.strip() != ""]
        i = 0
        while True:
            x = listret[i]
            if x[:5] == " and "  and len(x) != 5:
                listret = listret[:i] + [" and ", x[5:]]  + listret[i+1:]
                i = 0
                continue
            if x[:4] == " or "   and len(x) != 4:
                listret = listret[:i] + [" or ",  x[4:]]  + listret[i+1:]
                i = 0
                continue
            if x[-5:] == " and " and len(x) != 5:
                listret = listret[:i] + [x[:-5], " and "] + listret[i+1:]
                i = 0
                continue
            if x[-4:] == " or "  and len(x) != 4:
                listret = listret[:i] + [x[:-4],  " or "] + listret[i+1:]
                i = 0
                continue
            if i >= (len(listret) - 1): break
            i += 1
        if len(listret) == 1:
            # If it's not changed, it will convert to string.
            listret = listret[0] # Don't do strip()
            if listret[0] == "(" and listret[-1] == ")":
                return __work1(listret[1:-1])
        return listret
    def __work2(listwk: list[str]):
        listwk = copy.deepcopy(listwk)
        for i, tmp in enumerate(listwk):
            if tmp[0] == "(" and tmp[-1] == ")":
                tmp = tmp[1:-1]
            listwk[i] = __work1(tmp)
            if isinstance(listwk[i], list):
                listwk[i] = __work2(listwk[i])
        return listwk
    sql_where_clauses = __work2([sql_where_clause, ])
    if isinstance(sql_where_clauses, str):
        sql_where_clauses = [sql_where_clauses, ]
    elif isinstance(sql_where_clauses, list) and len(sql_where_clauses) == 1 and isinstance(sql_where_clauses[0], list):
        sql_where_clauses = sql_where_clauses[0]
    """
    >>> sql_where_clauses
    [
        "gender in ('male', 'female', 0)",
        ' and ',
        "name = 'Taro'",
        ' and ',
        [
            "department = 'Sales' and age > 30", 
            ' or ',
            [
                "department = 'Engineering'",
                ' and ',
                "salary > 70000 or position IN ('Manager', 'Lead Engineer')"
            ]
        ],
        ' and ',
        "location = 'New York' or location = 'San Francisco'"
    ]
    """
    def __work3(clauses: list[str | list]):
        if len(clauses) == 1:
            return parse_conditions(clauses[0])
        strop, listwk = None, []
        for i, clause in enumerate(clauses):
            if i % 2 == 1:
                if strop is None:
                    strop = clause
                else:
                    assert strop == clause # Operator must be one.
            else:
                if isinstance(clause, str):
                    listwk.append(parse_conditions(clause))
                elif isinstance(clause, list):
                    listwk.append(__work3(clause))
                else:
                    raise ValueError(f"This is not expected. [{clause}]")
        return {
            OPERATORS_MONGO[strop.strip()]: listwk
        }
    return __work3(sql_where_clauses)

def create_multi_condition(idxs: pd.DataFrame | pd.MultiIndex):
    sql = None
    def __check(x):
        if check_type(x, [int, str, np.int8, np.int16, np.int32, np.int64]):
            return str(x)
        elif check_type(x, str):
            return f"'{x}'"
        elif check_type(x, [datetime.datetime, pd._libs.tslibs.timestamps.Timestamp]):
            return f"'{x.strftime('%Y-%m-%d %H:%M:%S.%f%z')}'"
        else:
            raise TypeError(f"type: {type(x)}, {x} is not expected !!")
    if isinstance(idxs, pd.DataFrame):
        sql = (
            "( " + ", ".join(idxs.columns.tolist()) + " ) IN ( " + 
            ",".join(["(" + ",".join([__check(y) for y in x]) + ")" for x in idxs.values]) +  
            " )"   
        )
    elif check_type(idxs, [pd.MultiIndex, pd.Index]):
        assert idxs.names is not None
        if len(idxs.names) > 1:
            sql = (
                "( " + ", ".join(list(idxs.names)) + " ) IN ( " + 
                ",".join(["(" + ",".join([__check(y) for y in x]) + ")" for x in idxs]) +  
                " )"   
            )
        else:
            sql = (f"{idxs.names[0]} IN ( " + ",".join([__check(x) for x in idxs]) +  " )")
    else:
        raise TypeError(f"input data type is not expected. {type(idxs)}")
    return sql

def to_str_timestamp(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for x in df.columns:
        if isinstance(df[x].dtype, pd.core.dtypes.dtypes.DatetimeTZDtype):
            df[x] = "%DATETIME%" + df[x].dt.strftime("%Y-%m-%d %H:%M:%S.%f%z")
    return df
