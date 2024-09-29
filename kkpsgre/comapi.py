import requests, re, json
import pandas as pd

# local package
from kkpsgre.util.com import check_type
from kkpsgre.psgre import DBConnector


__all__ = [
    "select",
    "insert",
    "exec",
    "delete",
]


def to_str_timestamp(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for x in df.columns:
        if isinstance(df[x].dtype, pd.core.dtypes.dtypes.DatetimeTZDtype):
            df[x] = "%DATETIME%" + df[x].dt.strftime("%Y-%m-%d %H:%M:%S.%f%z")
    return df

def select(src: DBConnector | str, sql: str) -> pd.DataFrame:
    assert check_type(src, [DBConnector, str])
    assert isinstance(sql, str)
    if isinstance(src, DBConnector):
        return src.select_sql(sql)
    else:
        assert re.search(r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?):([0-9]{1,5})$", src) is not None
        res = requests.post(f"http://{src}/select", json={"sql": sql}, headers={'Content-type': 'application/json'})
        return pd.DataFrame(json.loads(res.json()))

def insert(src: DBConnector | str, df: pd.DataFrame, tblname: str, is_select: bool, add_sql: str=None):
    assert check_type(src, [DBConnector, str])
    assert isinstance(df, pd.DataFrame)
    assert isinstance(tblname, str)
    assert isinstance(is_select, bool)
    assert add_sql is None or isinstance(add_sql, str) # add_sql is only for "DELETE"
    if isinstance(src, DBConnector):
        if add_sql is not None: src.delete_sql(tblname, str_where=add_sql, set_sql=True)
        src.insert_from_df(df, tblname, set_sql=True, str_null="", is_select=is_select)
        src.execute_sql()
    else:
        assert re.search(r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?):([0-9]{1,5})$", src) is not None
        dictwk = {
            "data": to_str_timestamp(df).replace({float("nan"): None}).to_dict(),
            "tblname": tblname, "is_select": is_select
        }
        if add_sql is not None: dictwk.update({"add_sql": add_sql})
        res = requests.post(f"http://{src}/insert", json=dictwk, headers={'Content-type': 'application/json'})
        assert res.status_code == 200

def exec(src: DBConnector | str, sql: str):
    assert check_type(src, [DBConnector, str])
    assert isinstance(sql, str)
    if isinstance(src, DBConnector):
        src.set_sql(sql)
        src.execute_sql()
    else:
        assert re.search(r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?):([0-9]{1,5})$", src) is not None
        res = requests.post(f"http://{src}/exec", json={"sql": sql}, headers={'Content-type': 'application/json'})
        assert res.status_code == 200

def delete(src: DBConnector | str, tblname: str, str_where: str = None):
    assert check_type(src, [DBConnector, str])
    assert isinstance(tblname,   str)
    assert str_where is None or isinstance(str_where, str)
    if isinstance(src, DBConnector):
        src.delete_sql(tblname, str_where=str_where, set_sql=True)
        src.execute_sql()
    else:
        assert re.search(r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?):([0-9]{1,5})$", src) is not None
        res = requests.post(f"http://{src}/delete", json={"tblname": tblname, "str_where": str_where}, headers={'Content-type': 'application/json'})
        assert res.status_code == 200
