import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
# local package
from kkpsgre.connector import DBConnector
from kklogger import set_logger


LOGGER  = set_logger(__name__)
DBNAME  = "testdb"
TBLNAME = "test_table"


def create_test_df_pandas():
    df = pd.DataFrame({
        "id": [
            1, 2, 3, 4, 5, 6
        ],
        "datetime_no_nan": [
            datetime(2023, 1, 1, 10, 0, 0, tzinfo=ZoneInfo("UTC")),
            datetime(2023, 5, 5, 12, 30, 0, tzinfo=ZoneInfo("America/New_York")),
            datetime(2024, 12, 31, 23, 59, 59, tzinfo=ZoneInfo("Asia/Tokyo")),
            datetime(2025, 7, 4, 18, 0, 0),
            datetime(2025, 7, 4, 18, 0, 0, tzinfo=ZoneInfo("Europe/Paris")),
            datetime(2026, 1, 1, 0, 0, 0, tzinfo=ZoneInfo("UTC")),
        ],
        "datetime_with_nan": [
            datetime(2023, 1, 2, 0, 0, 0),
            None,
            datetime(2024, 1, 1, 13, 30, 30, tzinfo=ZoneInfo("Asia/Tokyo")),
            None,
            datetime(2023, 12, 31, 23, 59, 59, tzinfo=ZoneInfo("America/Los_Angeles")),
            datetime(2023, 12, 31, 23, 59, 59, tzinfo=ZoneInfo("Europe/Paris")),
        ],
        "int_no_nan": [
            0,
            100,
            -50,
            999999,
            2**31 - 1,  # 32bit int max
            -2**31,     # 32bit int min
        ],
        "int_with_nan": pd.Series([42, None, 0, 123456, None, -999], dtype="Int64"),
        "float_no_nan": [
            1.23,
            1e20,      
            1e-20,     
            np.inf,    
            -np.inf,   
            9999.9999,
        ],
        "float_with_nan": [
            None,
            0.1,
            np.pi,
            -42.42,
            1e-10,
            1e-5,
        ],
        "str_no_nan": [
            "Hello",
            "123'ABC",                 
            "Special chars: !@#$%^&*()",
            "日本語\n改行",
            "Emoji🔥 \"quoted\" text",
            "Mixedあいう123\\slash"
        ],
        "str_with_nan": [
            None,
            "foo's bar",
            None,
            "line1\nline2",
            "He said \"Hi\"",
            "escape\\slash"
        ],
        "bool_no_nan": [
            True,
            False,
            True,
            True,
            False,
            True
        ],
        "bool_with_nan": [
            False,
            None,
            True,
            None,
            False,
            True
        ],
        "category_column": pd.Series(["A", "B", "A", "C", "B", "A"], dtype="category")
    })
    return df


if __name__ == "__main__":
    df_org   = create_test_df_pandas()
    db_psgre = DBConnector("99.99.0.2", port=5432,  dbname=DBNAME, user="postgres", password="postgres", dbtype="psgre", max_disp_len=5000)
    db_mysql = DBConnector("99.99.0.3", port=3306,  dbname=DBNAME, user="mysql",    password="mysql",    dbtype="mysql", max_disp_len=5000)
    db_mongo = DBConnector("99.99.0.4", port=27017, dbname=DBNAME, user="root",     password="secret",   dbtype="mongo", max_disp_len=5000)

    LOGGER.info("DELETE", color=["BOLD", "GREEN"])
    db_psgre.delete_sql(TBLNAME, str_where="id in (1,2,3,4,5,6)")
    db_psgre.execute_sql()
    db_mysql.delete_sql(TBLNAME, str_where="id in (1,2,3,4,5,6)")
    db_mysql.execute_sql()
    db_mongo.delete_sql(TBLNAME, str_where="id in (1,2,3,4,5,6)")
    db_mongo.execute_sql()

    LOGGER.info("SELECT", color=["BOLD", "GREEN"])
    LOGGER.info(db_psgre.select_sql(f"SELECT * FROM {TBLNAME}"))
    LOGGER.info(db_mysql.select_sql(f"SELECT * FROM {TBLNAME}"))
    LOGGER.info(db_mongo.select_sql(f"SELECT * FROM {TBLNAME}"))

    LOGGER.info("INSERT", color=["BOLD", "GREEN"])
    db_psgre.insert_from_df(df_org, TBLNAME, set_sql=False, n_round=30)
    db_mysql.insert_from_df(df_org, TBLNAME, set_sql=False, n_round=30)
    db_mongo.insert_from_df(df_org, TBLNAME, set_sql=False, n_round=30)

    LOGGER.info("SELECT & CHECK DIFFENRENCES BETWEEN SELECTED AND ORIGINAL", color=["BOLD", "GREEN"])
    LOGGER.info("PostgreSQL", color=["BOLD", "CYAN"])
    df = db_psgre.select_sql(f"SELECT {','.join(df_org.columns.tolist())} FROM {TBLNAME}")
    assert df["id"].equals(df_org["id"])
    assert df["datetime_no_nan"].equals(
        pd.to_datetime(df_org["datetime_no_nan"].apply(lambda x: pd.Timestamp(x).tz_localize('UTC') if x.tzinfo is None else x), utc=True).dt.tz_convert(timezone(timedelta(hours=9)))
    )
    assert df["datetime_with_nan"].equals(
        pd.to_datetime(df_org["datetime_with_nan"].apply(lambda x: pd.Timestamp(x).tz_localize('UTC') if x is None or x.tzinfo is None else x), utc=True).dt.tz_convert(timezone(timedelta(hours=9)))
    )
    assert df["int_no_nan"].equals(df_org["int_no_nan"])
    assert df["int_with_nan"].equals(df_org["int_with_nan"].astype(float))
    assert np.allclose(df["float_no_nan"].fillna(-1).to_numpy(dtype=float), df_org["float_no_nan"].replace([np.inf, -np.inf], np.nan).fillna(-1).to_numpy(dtype=float))
    assert np.allclose(df["float_with_nan"].fillna(-1).to_numpy(dtype=float), df_org["float_with_nan"].fillna(-1).to_numpy(dtype=float))
    assert df["str_no_nan"].equals(df_org["str_no_nan"])
    assert df["str_with_nan"].equals(df_org["str_with_nan"])
    assert df["bool_no_nan"].equals(df_org["bool_no_nan"])
    assert df["bool_with_nan"].equals(df_org["bool_with_nan"])
    assert df["category_column"].equals(df_org["category_column"].astype(str))

    LOGGER.info("MySQL", color=["BOLD", "CYAN"])
    df = db_mysql.select_sql(f"SELECT {','.join(df_org.columns.tolist())} FROM {TBLNAME}")
    assert df["id"].equals(df_org["id"])
    assert df["datetime_no_nan"].equals(
        pd.to_datetime(df_org["datetime_no_nan"].apply(lambda x: pd.Timestamp(x).tz_localize('UTC') if x.tzinfo is None else x), utc=True).dt.tz_convert(timezone(timedelta(hours=0)))
    )
    assert df["datetime_with_nan"].equals(
        pd.to_datetime(df_org["datetime_with_nan"].apply(lambda x: pd.Timestamp(x).tz_localize('UTC') if x is None or x.tzinfo is None else x), utc=True).dt.tz_convert(timezone(timedelta(hours=0)))
    )
    assert df["int_no_nan"].equals(df_org["int_no_nan"])
    assert df["int_with_nan"].equals(df_org["int_with_nan"].astype(float))
    assert np.allclose(df["float_no_nan"].fillna(-1).to_numpy(dtype=float), df_org["float_no_nan"].replace([np.inf, -np.inf], np.nan).fillna(-1).to_numpy(dtype=float))
    assert np.allclose(df["float_with_nan"].fillna(-1).to_numpy(dtype=float), df_org["float_with_nan"].fillna(-1).to_numpy(dtype=float))
    assert df["str_no_nan"].equals(df_org["str_no_nan"])
    assert df["str_with_nan"].equals(df_org["str_with_nan"])
    assert df["bool_no_nan"].astype(bool).equals(df_org["bool_no_nan"])
    assert df["bool_with_nan"].astype(object).replace({float("nan"): None}).apply(lambda x: bool(x) if x is not None else None).equals(df_org["bool_with_nan"])
    assert df["category_column"].equals(df_org["category_column"].astype(str))

    LOGGER.info("MongoDB", color=["BOLD", "CYAN"])
    df = db_mongo.select_sql(f"SELECT {','.join(df_org.columns.tolist())} FROM {TBLNAME}")
    assert df["id"].equals(df_org["id"])
    assert df["datetime_no_nan"].equals(
        pd.to_datetime(df_org["datetime_no_nan"].apply(lambda x: pd.Timestamp(x).tz_localize('UTC') if x.tzinfo is None else x), utc=True).dt.tz_convert(timezone(timedelta(hours=0)))
    )
    assert df["datetime_with_nan"].equals(
        pd.to_datetime(df_org["datetime_with_nan"].apply(lambda x: pd.Timestamp(x).tz_localize('UTC') if x is None or x.tzinfo is None else x), utc=True).dt.tz_convert(timezone(timedelta(hours=0)))
    )
    assert df["int_no_nan"].equals(df_org["int_no_nan"])
    assert df["int_with_nan"].equals(df_org["int_with_nan"].astype(float))
    assert df["float_no_nan"].equals(df_org["float_no_nan"])
    assert np.allclose(df["float_with_nan"].fillna(-1).to_numpy(dtype=float), df_org["float_with_nan"].fillna(-1).to_numpy(dtype=float))
    assert df["str_no_nan"].equals(df_org["str_no_nan"])
    assert df["str_with_nan"].equals(df_org["str_with_nan"])
    assert df["bool_no_nan"].astype(bool).equals(df_org["bool_no_nan"])
    assert df["bool_with_nan"].astype(object).replace({float("nan"): None}).apply(lambda x: bool(x) if x is not None else None).equals(df_org["bool_with_nan"])
    assert df["category_column"].equals(df_org["category_column"].astype(str))
