import pandas as pd
import numpy as np
from joblib import Parallel, delayed
from functools import partial

# local package
from kkpsgre.util.com import check_str_is_integer, check_type_list, check_type


__all__ = [
    "parallel_apply",
    "drop_duplicate_columns",
    "apply_fill_missing_values",
    "check_column_is_integer",
    "check_column_is_float",
    "correct_round_values",
    "to_string_all_columns",
]


LIST_NUM_TYPES = [int, float, np.int8, np.int16, np.int32, np.int64, np.float16, np.float32, np.float64, np.float128]


def parallel_apply(df: pd.DataFrame, func, axis: int=0, group_key=None, func_aft=None, batch_size: int=1, n_jobs: int=1):
    """
    pandarallel is slow in some cases. It is twice as fast to use pandas.
    Params::
        func:
            ex) lambda x: x.rank()
        axis:
            axis=0: df.apply(..., axis=0)
            axis=1: df.apply(..., axis=1)
            axis=2: df.groupby(...)
        func_aft:
            input: (list_object, index, columns)
            ex) lambda x,y,z: pd.concat(x, axis=1, ignore_index=False, sort=False).loc[:, z]
    """
    assert isinstance(df, pd.DataFrame)
    assert isinstance(axis, int) and axis in [0, 1, 2]
    if axis == 2: assert group_key is not None and check_type_list(group_key, str)
    assert isinstance(batch_size, int) and batch_size >= 1
    assert isinstance(n_jobs, int) and n_jobs > 0
    if   axis == 0: batch_size = min(df.shape[1], batch_size)
    elif axis == 1: batch_size = min(df.shape[0], batch_size)
    index, columns = df.index, df.columns
    list_object = None
    if   axis == 0:
        batch = np.arange(df.shape[1])
        if batch_size > 1: batch = np.array_split(batch, batch.shape[0] // batch_size)
        else: batch = batch.reshape(-1, 1)
        list_object = Parallel(n_jobs=n_jobs, backend="loky", verbose=10, batch_size="auto")([delayed(func)(df.iloc[:, i_batch]) for i_batch in batch])
    elif axis == 1:
        batch = np.arange(df.shape[0])
        if batch_size > 1: batch = np.array_split(batch, batch.shape[0] // batch_size)
        else: batch = batch.reshape(-1, 1)
        list_object = Parallel(n_jobs=n_jobs, backend="loky", verbose=10, batch_size="auto")([delayed(func)(df.iloc[i_batch   ]) for i_batch in batch])
    else:
        if len(group_key) == 1: group_key = group_key[0]
        list_object = Parallel(n_jobs=n_jobs, backend="loky", verbose=10, batch_size=batch_size)([delayed(func)(dfwk) for *_, dfwk in df.groupby(group_key)])
    if len(list_object) > 0 and func_aft is not None:
        return func_aft(list_object, index, columns)
    else:
        return list_object

def drop_duplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicate columns.
    When retrieved from a database, the same column name can exist.
    """
    assert isinstance(df, pd.DataFrame)
    list_bool, listwk = [], []
    for x in df.columns:
        if (df.columns == x).sum() == 1:
            list_bool.append(True)
            listwk.append(x)
        else:
            if x in listwk:
                list_bool.append(False)
            else:
                list_bool.append(True)
                listwk.append(x)
    return df.loc[:, list_bool]

def apply_fill_missing_values(df: pd.DataFrame, rep_nan: str, rep_inf: str, rep_minf: str, dtype=object, batch_size: int=1, n_jobs: int=1) -> pd.DataFrame:
    assert isinstance(df, pd.DataFrame)
    assert isinstance(batch_size, int) and batch_size >= 1
    assert isinstance(n_jobs, int) and n_jobs >= 1
    assert isinstance(rep_nan,  str)
    assert isinstance(rep_inf,  str)
    assert isinstance(rep_minf, str)
    df = df.astype(object).copy()
    func1 = partial(apply_fill_missing_values_func1, rep_nan=rep_nan, rep_inf=rep_inf, rep_minf=rep_minf, dtype=dtype)
    if n_jobs == 1:
        return func1(df)
    else:
        return parallel_apply(
            df, func1,
            func_aft=lambda x,y,z: pd.concat(x, axis=1, ignore_index=False, sort=False).loc[:, z], axis=0, batch_size=batch_size, n_jobs=n_jobs
        )
# The aim of vectorize_to_int is converting df type object and disticting integer and float type in object column.
# The integer value can be almost converted to value without "e" format. but float is still having...
# >>> str(int(1e20))
# '100000000000000000000'
# >>> str(float(0.0000001))
# '1e-07'
vectorize_to_int = np.vectorize(lambda x: (int(x) if float.is_integer(float(x)) else float(x)) if check_type(x, LIST_NUM_TYPES) else x, otypes=[object])
def apply_fill_missing_values_func1(ins: pd.DataFrame | pd.Series, rep_nan: str=None, rep_inf: str=None, rep_minf: str=None, dtype=None):
    if dtype == str:
        y = ins.replace(float("nan"), rep_nan).replace(float("inf"), rep_inf).replace(float("-inf"), rep_minf) # replace(float("nan"), "") can replace None to "". pd.DataFrame(["aa", 1,2,3, None, 1.1111, float("nan")]).replace(float("nan"), "")
        if isinstance(y, pd.DataFrame): # after fillna(rep_nan), the column which has string (but originaly from datetime64[ns]) type become back datetime64[ns] automaticaly
            for x in y.columns:
                if pd.api.types.is_datetime64_ns_dtype(y[x]): y[x] = y[x].astype(str) # If x is datetime and df[x].values.tolist() run, the date goes to integer. I don't know why.
        elif isinstance(y, pd.Series):
            if pd.api.types.is_datetime64_ns_dtype(y): y = y.astype(str) 
        y = vectorize_to_int(y.values.tolist())
        if isinstance(ins, pd.DataFrame):
            y = pd.DataFrame(y, index=ins.index, columns=ins.columns, dtype=dtype)
        elif isinstance(ins, pd.Series):
            y = pd.Series(y, index=ins.index, dtype=dtype)
        else:
            raise Exception(f"unexpected class: {ins.__class__}")
    else:
        y = ins.replace(float("nan"), rep_nan).replace(float("inf"), rep_inf).replace(float("-inf"), rep_minf).astype(dtype)
    return y

def check_column_is_integer(se: pd.Series, except_strings: list[str] = [""]) -> pd.Series:
    se_bool = (se.str.contains(r"^[0-9]$",     regex=True) | se.str.contains(r"^-[1-9]$",     regex=True) | \
               se.str.contains(r"^[0-9]\.0+$", regex=True) | se.str.contains(r"^-[0-9]+\.0+$", regex=True) | \
               se.str.contains(r"^[1-9][0-9]+$",     regex=True) | se.str.contains(r"^-[1-9][0-9]+$", regex=True) | \
               se.str.contains(r"^[1-9][0-9]+\.0+$", regex=True) | se.str.contains(r"^-[1-9][0-9]+\.0+$", regex=True))
    se_bool = se_bool & (se.str.zfill(len("9223372036854775807")) <= "9223372036854775807")
    for x in except_strings: se_bool = se_bool | (se == x)
    return se_bool

def check_column_is_float(se: pd.Series, except_strings: list[str] = [""]) -> pd.Series:
    se_bool = (se.str.contains(r"^[0-9]\.[0-9]+$",       regex=True) | se.str.contains(r"^-[0-9]\.[0-9]+$",       regex=True) | \
               se.str.contains(r"^[1-9][0-9]+\.[0-9]+$", regex=True) | se.str.contains(r"^-[1-9][0-9]+\.[0-9]+$", regex=True))
    for x in except_strings: se_bool = se_bool | (se == x)
    return se_bool

def correct_round_values(df: pd.DataFrame, strtmp: str=None, rep_nan: str=None, n_round: int=None):
    df = df.copy()
    list_se = []
    for x in df.columns:
        se = df[x]
        if   check_column_is_integer(se, except_strings=[rep_nan]).sum() == se.shape[0]:
            # don't use under astype(np.float32)
            se = se.replace(rep_nan, strtmp, inplace=False, regex=False).astype(np.float128).astype(np.int64).astype(str).replace(strtmp, rep_nan, regex=False)
        elif check_column_is_float(  se, except_strings=[rep_nan]).sum() == se.shape[0]:
            se =  se.replace(rep_nan, np.nan, inplace=False, regex=False).astype(np.float64).round(n_round).astype(str).replace(str(np.nan), rep_nan, regex=False)
        list_se.append(se)
    return pd.concat(list_se, axis=1).loc[:, df.columns]

def to_string_all_columns(
    df: pd.DataFrame, n_round=3, rep_nan: str="%%null%%", rep_inf: str="%%null%%", rep_minf: str="%%null%%", 
    strtmp: str="-9999999", batch_size: int=1, n_jobs: int=1
) -> pd.DataFrame:
    """
    We originally want to display int values as integers, for example when displaying them on the screen.
    However, if nan is included, the display of integers is broken because it becomes a float type column.
    So, we convert all nan and adjust the int ones to be integers.
    Params::
        df:
            input dataframe
        n_round:
            Number of digits to round numbers
        rep_nan:
            Special string to replace missing values
        rep_inf:
            Special string to replace infinity values
        rep_minf:
            Special string to replace minus infinity values
        strtmp:
            Special numeric character that temporarily replaces a missing value in order to convert all dataframe data to string.
    """
    assert isinstance(df, pd.DataFrame)
    assert isinstance(n_round, int) and n_round >= 0
    assert isinstance(rep_nan, str)
    assert isinstance(rep_inf, str)
    assert isinstance(rep_minf, str)
    assert isinstance(strtmp, str) and check_str_is_integer(strtmp)
    assert isinstance(batch_size, int) and batch_size >= 1
    assert isinstance(n_jobs, int) and n_jobs >= 1
    df = df.copy()
    columns_org = df.columns.copy()
    # 1) The float column rounds. The type is preserved and only the float type is processed.
    columns = df.columns[(df.dtypes == float) | (df.dtypes == np.float16) | (df.dtypes == np.float32) | (df.dtypes == np.float64)].values.copy()
    if len(columns) > 0:
        df_target = df.loc[:, columns].copy()
        df_target = df_target.round(n_round)
        for x in columns: df[x] = df_target[x].values
    # 2) I want to convert boolean to int in advance, and insert 0, 1 or null value when csv copy.
    columns = df.columns[(df.dtypes == bool)].values.copy()
    if len(columns) > 0:
        df_target = df.loc[:, columns].copy()
        df_target = df_target.astype(np.int8)
        for x in columns: df[x] = df_target[x].values
    # 3) Fill nan, inf, -inf value, and convert dataframe to string.
    df = apply_fill_missing_values(df, rep_nan, rep_inf, rep_minf, dtype=str, batch_size=batch_size, n_jobs=n_jobs)
    if (df == strtmp).sum(axis=0).sum() > 0:
        raise Exception(f"strtmp: {strtmp} exist.")
    # 4) For strings with only numbers, convert nan to strtmp once, then convert to numeric strings and correct the values.
    func1 = partial(correct_round_values, strtmp=strtmp, rep_nan=rep_nan, n_round=n_round)
    if n_jobs == 1:
        df = func1(df)
    else:
        df = parallel_apply(
            df, func1,
            func_aft=lambda x,y,z: pd.concat(x, axis=1, ignore_index=False, sort=False).loc[:, z], axis=0, batch_size=1, n_jobs=n_jobs
        )
    df = df.loc[:, columns_org]
    return df
