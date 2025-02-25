import pandas as pd
import mysql.connector
import psycopg2
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
    db_mysql.delete_sql(TBLNAME, str_where="id in (1,2,3,4,5,6)", set_sql=False)
    db_psgre.insert_from_df(df_org, TBLNAME, set_sql=False, is_select=True)
    db_mysql.insert_from_df(df_org, TBLNAME, set_sql=False, is_select=True)
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
