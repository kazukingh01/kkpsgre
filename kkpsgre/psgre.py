import psycopg2
import re
from typing import List
import pandas as pd
import numpy as np

# local package
from kkpsgre.util.dataframe import drop_duplicate_columns, to_string_all_columns
from kkpsgre.util.com import check_type_list, strfind
from kkpsgre.util.logger import set_logger
LOGNAME = __name__


__all__ = [
    "Psgre",
]


class Psgre:
    def __init__(self, connection_string: str, max_disp_len: int=100, kwargs_psgre: dict={}, **kwargs):
        """
        DataFrame interface class for PostgresSQL.
        Params::
            connection_string:
                ex) host=172.18.10.2 port=5432 dbname=boatrace user=postgres password=postgres
        Note::
            If connection_string = None, empty update is enable.
        """
        assert connection_string is None or isinstance(connection_string, str)
        assert isinstance(max_disp_len, int)
        self.connection_string = connection_string
        self.con               = None if connection_string is None else psycopg2.connect(connection_string, **kwargs_psgre)
        self.max_disp_len      = max_disp_len
        self.logger            = set_logger(f"{LOGNAME}.{self.__class__.__name__}.{str(id(self.con))}", **kwargs)
        self.initialize()
        if connection_string is None:
            self.logger.info("dummy connection is established.")
        else:
            self.logger.info(f'connection is established. {connection_string[:connection_string.find("password")]}')

    def initialize(self):
        self.sql_list = [] # After setting a series of sql, we'll execute them all at once.(insert, update, delete)

    def __del__(self):
        if self.con is not None:
            self.con.close()

    def raise_error(self, msg: str, exception = Exception):
        """ Implement your own to break the connection. """
        self.__del__()
        self.logger.raise_error(msg, exception)

    def check_status(self, check_list: List[str]=["open"]):
        assert check_type_list(check_list, str)
        for x in check_list: assert x in ["open", "lock", "esql"]
        if self.con is not None:
            if "open" in check_list and self.con.closed == 1:
                self.raise_error("connection is closed.")
            if "lock" in check_list and len(self.sql_list) > 0:
                self.raise_error("sql_list is not empty. you can do after ExecuteSQL().")
            if "esql" in check_list and len(self.sql_list) == 0:
                self.raise_error("sql_list is empty. you set executable sql.")

    def display_sql(self, sql: str) -> str:
        assert isinstance(sql, str)
        return ("SQL:" + sql[:self.max_disp_len] + " ..." + sql[-self.max_disp_len:] if len(sql) > self.max_disp_len*2 else sql)

    def select_sql(self, sql: str) -> pd.DataFrame:
        assert isinstance(sql, str)
        self.check_status(["open","lock"])
        df = pd.DataFrame()
        if strfind(r"^select", sql, flags=re.IGNORECASE):
            self.logger.debug(f"SQL START: {self.display_sql(sql)}")
            if self.con is not None:
                self.con.autocommit = True # Autocommit ON because even references are locked in principle.
                cur = self.con.cursor()
                cur.execute(sql)
                df = pd.DataFrame(cur.fetchall())
                if df.shape == (0, 0):
                    df = pd.DataFrame(columns=[x.name for x in cur.description])
                else:
                    df.columns = [x.name for x in cur.description]
                cur.close()
                self.logger.debug(f"SQL END")
                self.con.autocommit = False
        else:
            self.raise_error(f"sql: {sql[:100]}... is not started 'SELECT'")
        df = drop_duplicate_columns(df)
        return df

    def set_sql(self, sql: List[str]):
        assert isinstance(sql, str) or isinstance(sql, list)
        if isinstance(sql, str): sql = [sql, ]
        for x in sql:
            if strfind(r"^select", x, flags=re.IGNORECASE):
                self.raise_error(self.display_sql(x) + ". you can't set 'SELECT' sql.")
            else:
                self.sql_list.append(x)

    def execute_sql(self, sql: str=None):
        """ Execute the contents of sql_list. """
        self.logger.info("START")
        assert sql is None or isinstance(sql, str)
        self.check_status(["open"])
        if sql is not None:
            self.check_status(["lock"])
            self.set_sql(sql)
        self.check_status(["esql"])
        if self.con is not None:
            self.con.autocommit = False
            cur = self.con.cursor()
            try:
                for x in self.sql_list:
                    self.logger.info(self.display_sql(x))
                    cur.execute(x)
                self.con.commit()
            except:
                self.con.rollback()
                cur.close()
                self.raise_error("sql error !!")
            cur.close()
        self.sql_list = []
        self.logger.info("END")

    def read_table_layout(self, tblname: str, system_colname_list: List[str] = ["sys_updated"]) -> pd.DataFrame:
        self.logger.debug("START")
        assert isinstance(tblname, str)
        sql = f"SELECT table_name as tblname, column_name as colname, data_type FROM information_schema.columns where table_schema = 'public' and table_name = '{tblname}' "
        for x in system_colname_list: sql += f"and column_name <> '{x}' "
        sql += "order by ordinal_position;"
        df = self.select_sql(sql)
        self.logger.debug("END")
        return df

    def execute_copy_from_df(
            self, df: pd.DataFrame, tblname: str, system_colname_list: List[str] = ["sys_updated"], 
            filename: str=None, encoding: str="utf8", n_round: int=3, 
            str_null :str="%%null%%", check_columns: bool=True, n_jobs: int=1
    ):
        """
        Params::
            df:
                input dataframe.
            tblname:
                table name.
            system_colname_list:
                special column names that does not insert.
                "sys_updated" is automatically inserted the update datetime.
            filename:
                temporary csv name to output
            encoding:
                "shift-jisx0213", "utf8", ...
            n_round:
                Number of digits to round numbers
            str_null:
                A special string that temporarily replaces NULL.
            check_columns:
                If True, check that all table columns are present in the datafarme.
                Else, all nan to create dataframe cplumns that do not exist in table columns.
            n_jobs:
                Number of workers used for parallelisation
        """
        self.logger.info("START")
        assert isinstance(df, pd.DataFrame)
        assert isinstance(tblname, str)
        assert check_type_list(system_colname_list, str)
        if filename is None: filename = f"./postgresql_copy.{str(id(self.con))}.csv"
        assert isinstance(filename, str)
        assert isinstance(encoding, str)
        assert isinstance(check_columns, bool)
        self.check_status(["open", "lock"])
        dfcol = self.read_table_layout(tblname, system_colname_list=system_colname_list)
        ndf   = np.isin(dfcol["colname"].values, df.columns.values)
        if check_columns:
            if (ndf == False).sum() > 0:
                self.raise_error(f'{dfcol["colname"].values[~ndf]} columns is not included in df: {df}.')
            df = df[dfcol["colname"].values].copy()
        else:
            # Create a column that does not exist in the table columns.
            df = df.loc[:, dfcol["colname"].values[ndf]].copy()
            for x in dfcol["colname"].values[~ndf]: df[x] = float("nan")
        df = to_string_all_columns(df, n_round=n_round, rep_nan=str_null, rep_inf=str_null, rep_minf=str_null, strtmp="-9999999", n_jobs=n_jobs)
        df = df.replace("\r\n", " ").replace("\n", " ").replace("\t", " ") # Convert line breaks and tabs to spaces.
        self.logger.info(f"start to copy from csv. table: {tblname}")
        df.to_csv(filename, encoding=encoding, quotechar="'", sep="\t", index=False, header=False)
        if self.con is not None:
            try:
                cur = self.con.cursor()
                with open(filename, mode="r", encoding=encoding) as f:
                    cur.copy_from(f, tblname, columns=tuple(df.columns.tolist()), sep="\t", null=str_null)
                self.con.commit() # Not sure if this code is needed.
                self.logger.info(f"finish to copy from csv. table: {tblname}")
            except:
                self.con.rollback() # Not sure if this code is needed.
                cur.close()
                self.raise_error("csv copy error !!")
        self.logger.info("END")
        return df

    def insert_from_df(self, df: pd.DataFrame, tblname: str, set_sql: bool=True, n_round: int=3, str_null :str="%%null%%", is_select: bool=False, n_jobs: int=1):
        """
        Params::
            df:
                input dataframe.
            tblname:
                table name.
            n_round:
                Number of digits to round numbers
            str_null:
                A special string that temporarily replaces NULL.
            n_jobs:
                Number of workers used for parallelisation
        """
        assert isinstance(df, pd.DataFrame)
        assert isinstance(tblname, str)
        assert isinstance(set_sql, bool)
        df = to_string_all_columns(df, n_round=n_round, rep_nan=str_null, rep_inf=str_null, rep_minf=str_null, strtmp="-9999999", n_jobs=n_jobs)
        if is_select:
            dfcol = self.read_table_layout(tblname)
            df    = df.loc[:, df.columns.isin(dfcol["colname"])].copy()
        sql = "insert into "+tblname+" ("+",".join(df.columns.tolist())+") values "
        for ndf in df.values:
            sql += "('" + "','".join(ndf.tolist()) + "'), "
        sql = sql[:-2] + "; "
        sql = sql.replace("'"+str_null+"'", "null")
        if set_sql: self.set_sql(sql)
        return sql
    
    def update_from_df(
        self, df: pd.DataFrame, tblname: str, columns_set: List[str], columns_where: List[str],
        set_sql: bool=True, n_round: int=3, str_null :str="%%null%%", n_jobs: int=1
    ):
        assert isinstance(df, pd.DataFrame)
        assert isinstance(tblname, str)
        assert isinstance(set_sql, bool)
        assert check_type_list(columns_set,   str)
        assert check_type_list(columns_where, str)
        df = to_string_all_columns(df, n_round=n_round, rep_nan=str_null, rep_inf=str_null, rep_minf=str_null, strtmp="-9999999", n_jobs=n_jobs)
        sql = ""
        for i in range(df.shape[0]):
            sql += f"update {tblname} set " + ", ".join([f"{x} = '{df[x].iloc[i]}'" for x in columns_set]) + " where " + " and ".join([f"{x} = '{df[x].iloc[i]}'" for x in columns_where]) + ";"
        sql = sql.replace("'"+str_null+"'", "null")
        if set_sql: self.set_sql(sql)
        return sql