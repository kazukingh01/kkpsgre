import re
import pandas as pd
# local package
from kkpsgre.util.com import check_type, check_type_list, str_to_datetime, strfind


__all__ = [
    "escape_mysql_reserved_word",
    "to_str_timestamp"
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
    "OR": "$or",
    "and": "$and",
    "or": "$or",
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
    
def find_matching_paren(s, start):
    stack = []
    for i in range(start, len(s)):
        if s[i] == '(':
            stack.append(i)
        elif s[i] == ')':
            stack.pop()
            if not stack:
                return i
    return -1

def parse_conditions(sql_where_clause):
    def __work(value):
        if value in DICT_CONV_MONGO:
            return DICT_CONV_MONGO[value]
        else:
            value = eval(value)
            if isinstance(value, str):
                try:
                    return str_to_datetime(value)
                except ValueError:
                    return value
            else:
                return value
    pattern = r"(\w+)\s*(!=|<>|<=|>=|<|>|=)\s*('?.*?'?)\s*(AND|OR|$)"
    matches = re.findall(pattern, sql_where_clause, re.IGNORECASE)
    current_operator   = None
    current_conditions = []
    mongo_query        = {}
    for match in matches:
        field, operator, value, logical_op = match # ex) field: aa, operator: >, value: 0, logical_op: and
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
    sql_query    = "(age >= 30 AND salary < 5000) OR name = 'John'"
    mongo_filter = sql_to_mongo_filter(sql_query)
    print(mongo_filter)
    """
    # devide (, )
    while '(' in sql_where_clause:
        start = sql_where_clause.index('(')
        end = find_matching_paren(sql_where_clause, start)
        if end == -1:
            raise ValueError("It's not end with ')'")
        inner_clause = sql_where_clause[start + 1:end]
        parsed_inner = parse_conditions(inner_clause)
        sql_where_clause = sql_where_clause[:start] + str(parsed_inner) + sql_where_clause[end + 1:]
    return parse_conditions(sql_where_clause)

def create_multi_condition(idxs: pd.DataFrame | pd.MultiIndex):
    sql = None
    def __check(x):
        if check_type(x, [int, str, np.int8, np.int16, np.int32, np.int64]):
            return x
        else:
            raise TypeError(f"type: {type(x)}, {x} is not expected !!")
    if isinstance(idxs, pd.DataFrame):
        sql = (
            "( " + ", ".join(idxs.columns.tolist()) + " ) IN ( " + 
            ",".join(["(" + ",".join([f"'{y}'" if isinstance(__check(y), str) else f"{y}" for y in x]) + ")" for x in idxs.values]) +  
            " )"   
        )
    elif isinstance(idxs, pd.MultiIndex):
        assert idxs.names is not None
        sql = (
            "( " + ", ".join(list(idxs.names)) + " ) IN ( " + 
            ",".join(["(" + ",".join([f"'{y}'" if isinstance(__check(y), str) else f"{y}" for y in x]) + ")" for x in idxs]) +  
            " )"   
        )
    else:
        raise TypeError(f"input data type is not expected. {type(idxs)}")
    return sql

def to_str_timestamp(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for x in df.columns:
        if isinstance(df[x].dtype, pd.core.dtypes.dtypes.DatetimeTZDtype):
            df[x] = "%DATETIME%" + df[x].dt.strftime("%Y-%m-%d %H:%M:%S.%f%z")
    return df
