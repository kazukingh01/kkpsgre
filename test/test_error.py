import pandas as pd
import numpy as np
import mysql.connector
import psycopg2
from datetime import timezone, timedelta
# local package
from test_sql_pandas import create_test_df_pandas
from kkpsgre.connector import DBConnector
from kklogger import set_logger


LOGGER  = set_logger(__name__)
DBNAME  = "testdb"
TBLNAME = "test_table"


if __name__ == "__main__":
    df_org   = create_test_df_pandas()
    db_psgre = DBConnector("99.99.0.2", port=5432,  dbname=DBNAME, user="postgres", password="postgres", dbtype="psgre", max_disp_len=5000, use_polars=False)
    db_mysql = DBConnector("99.99.0.3", port=3306,  dbname=DBNAME, user="mysql",    password="mysql",    dbtype="mysql", max_disp_len=5000, use_polars=False)
    db_psgre.delete_sql(TBLNAME, str_where="id in (1,2,3,4,5,6)", set_sql=False)
    db_psgre.execute_copy_from_df(df_org, TBLNAME, filename="tmp.csv", encoding="utf-8", check_columns=True, n_jobs=1)
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
    assert df["str_no_nan"  ].equals(df_org["str_no_nan"  ].replace(r"\r\n", " ", regex=True).replace(r"\n", " ", regex=True).replace(r"\t", " ", regex=True).replace(r"\\", " ", regex=True))
    assert df["str_with_nan"].equals(df_org["str_with_nan"].replace(r"\r\n", " ", regex=True).replace(r"\n", " ", regex=True).replace(r"\t", " ", regex=True).replace(r"\\", " ", regex=True))
    assert df["bool_no_nan"].equals(df_org["bool_no_nan"])
    assert df["bool_with_nan"].equals(df_org["bool_with_nan"])
    assert df["category_column"].equals(df_org["category_column"].astype(str))

    db_psgre.delete_sql(TBLNAME, str_where="id in (1,2,3,4,5,6)", set_sql=False)
    db_mysql.delete_sql(TBLNAME, str_where="id in (1,2,3,4,5,6)", set_sql=False)
    db_psgre.insert_from_df(df_org, TBLNAME, set_sql=False, is_select=True)
    db_mysql.insert_from_df(df_org, TBLNAME, set_sql=False, is_select=True)
    df_org["str_no_nan"  ] = "aa"
    df_org["str_with_nan"] = "bb"
    db_psgre.update_from_df(df_org, TBLNAME, columns_set=["str_no_nan", "str_with_nan"], columns_where=["id", "int_no_nan"], set_sql=False)
    db_mysql.update_from_df(df_org, TBLNAME, columns_set=["str_no_nan", "str_with_nan"], columns_where=["id", "int_no_nan"], set_sql=False)
    dfwk = db_psgre.select_sql('select * from test_table;')
    assert (dfwk["str_no_nan"  ] == "aa").sum() == dfwk.shape[0]
    assert (dfwk["str_with_nan"] == "bb").sum() == dfwk.shape[0]
    dfwk = db_mysql.select_sql('select * from test_table;')
    assert (dfwk["str_no_nan"  ] == "aa").sum() == dfwk.shape[0]
    assert (dfwk["str_with_nan"] == "bb").sum() == dfwk.shape[0]
    df_org.loc[0, "id"] = 2
    try:
        LOGGER.info(f"PostgreSQL", color=["BOLD", "GREEN"])
        db_psgre.delete_sql(TBLNAME, str_where="id in (1,2,3,4,5,6)", set_sql=True)
        db_psgre.insert_from_df(df_org, TBLNAME, set_sql=True, is_select=True)
        db_psgre.execute_sql()
        assert False # This is unexpected error.
    except psycopg2.errors.UniqueViolation as e:
        LOGGER.info(f"Check below if the data is same before the query ran. This is correct error", color=["BOLD", "CYAN"])
        db_psgre = DBConnector("99.99.0.2", port=5432,  dbname=DBNAME, user="postgres", password="postgres", dbtype="psgre", max_disp_len=5000, use_polars=False)
        LOGGER.info(f"{db_psgre.select_sql('select * from test_table;')}")
    try:
        LOGGER.info(f"MySQL", color=["BOLD", "GREEN"])
        db_mysql.delete_sql(TBLNAME, str_where="id in (1,2,3,4,5,6)", set_sql=True)
        db_mysql.insert_from_df(df_org, TBLNAME, set_sql=True, is_select=True)
        db_mysql.execute_sql()
        assert False # This is unexpected error.
    except mysql.connector.errors.IntegrityError as e:
        LOGGER.info(f"Check below if the data is same before the query ran. This is correct error", color=["BOLD", "CYAN"])
        db_mysql = DBConnector("99.99.0.3", port=3306,  dbname=DBNAME, user="mysql",    password="mysql",    dbtype="mysql", max_disp_len=5000, use_polars=False)
        LOGGER.info(f"{db_mysql.select_sql('select * from test_table;')}")
