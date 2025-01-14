import psycopg2, re, datetime
import mysql.connector
import pandas as pd
import numpy as np
import polars as pl
import pymongo

# local package
from kkpsgre.util.dataframe import drop_duplicate_columns, to_string_all_columns
from kkpsgre.util.com import check_type_list, strfind, find_matching_words
from kkpsgre.util.sql import escape_mysql_reserved_word, sql_to_mongo_filter
from kklogger import set_logger
LOGNAME = __name__


__all__ = [
    "DBConnector",
]


DBTYPES = ["psgre", "mysql", "mongo"]
RESERVED_WORD_MYSQL = [
    "interval", "explain", "long", "short"
]
RESERVED_WORD_PSGRE = []


class CustomSQLException(Exception):
    pass

class DBConnector:
    def __init__(
            self,
            host: str,
            port: int=None,
            dbname: str=None,
            user: str=None,
            password: str=None,
            dbtype: str="psgre",
            max_disp_len: int=100,
            kwargs_db: dict={},
            is_read_layout: bool=True,
            use_polars: bool = False,
            **kwargs
        ):
        """
        DataFrame interface class for PostgresSQL / MySQL / MongoDB.
        Params::
            connection_string:
                ex) host=172.18.10.2 port=5432 dbname=boatrace user=postgres password=postgres
        Note::
            If connection_string = None, empty update is enable.
        """
        assert host is None or isinstance(host, str)
        if host is not None:
            assert isinstance(port, int)
            assert isinstance(dbname, str)
            assert isinstance(user, str)
            assert isinstance(password, str)
        assert isinstance(dbtype, str) and dbtype in DBTYPES
        assert isinstance(max_disp_len, int)
        assert isinstance(is_read_layout, bool)
        assert isinstance(use_polars, bool)
        self.dbinfo = {
            "host": host,
            "port": port,
            "dbname": dbname,
            "user": user,
            "dbtype": dbtype,
        }
        self.con = None
        if   host is not None and dbtype == "psgre":
            self.con = psycopg2.connect(f"host={host} port={port} dbname={dbname} user={user} password={password}", **kwargs_db)
        elif host is not None and dbtype == "mysql":
            self.con = mysql.connector.connect(user=user, password=password, host=host, port=port, database=dbname)
        elif host is not None and dbtype == "mongo":
            self.con = pymongo.MongoClient(f"mongodb://{user}:{password}@{host}:{port}/?authSource=admin")[dbname]
        self.max_disp_len   = max_disp_len
        self.is_read_layout = is_read_layout
        self.use_polars     = use_polars
        self.logger         = set_logger(f"{LOGNAME}.{self.__class__.__name__}.{datetime.datetime.now().timestamp()}", **kwargs)
        if self.con is None:
            self.logger.info("dummy connection is established.")
        else:
            self.logger.info(f'connection is established. {self.dbinfo}')
        self.sql_list = []
        self.initialize()

    def initialize(self):
        self.logger.info("START")
        self.sql_list = [] # After setting a series of sql, we'll execute them all at once.(insert, update, delete)
        if self.con is not None and self.is_read_layout:
            if self.dbinfo["dbtype"] in ["psgre", "mysql"]:
                df = self.read_table_layout()
                self.db_layout      = {x: y.tolist() for x, y in df.groupby("tblname")["colname"]}
                self.db_layout_type = {x: {a: b for a, b in y.values} for x, y in df.groupby("tblname")[["colname", "data_type"]]}
                df = self.read_table_constraint()
                self.db_constraint  = {x: y.tolist() for x, y in df.groupby("table_name")["column_name"]}
            elif self.dbinfo["dbtype"] in ["mongo"]:
                self.db_layout      = {x: self.select_sql(f"SELECT * FROM {x} LIMIT 1;", ret_polars=False).columns.tolist() for x in self.con.list_collection_names() if x.find("system") != 0}
                self.db_layout_type = {}
                self.db_constraint  = {x: None for x in self.con.list_collection_names() if x.find("system") != 0}
        else:
            self.db_layout     = {}
            self.db_constraint = {}
        self.logger.info("END")
    
    def __del__(self):
        if self.con is not None and self.is_closed() == False:
            if self.dbinfo["dbtype"] in ["psgre", "mysql"]:
                self.con.close()
            elif self.dbinfo["dbtype"] in ["mongo"]:
                self.con.client.close()
            self.logger.info("DB connection close successfully.")
    
    def is_closed(self):
        boolwk = False
        if   self.dbinfo["dbtype"] == "psgre":
            boolwk = (self.con.closed == 1)
        elif self.dbinfo["dbtype"] == "mysql":
            boolwk = self.con.is_closed()
        elif self.dbinfo["dbtype"] == "mongo":
            try:
                self.con.client.server_info()
            except (pymongo.errors.InvalidOperation, pymongo.errors.ServerSelectionTimeoutError, ImportError) as e:
                boolwk = True
            except Exception as e:
                self.logger.raise_error("Something happens.", e)
        return boolwk

    def raise_error(self, msg: str, exception: Exception = Exception):
        """ Implement your own to break the connection. """
        self.__del__()
        self.logger.raise_error(msg, exception)

    def check_status(self, check_list: list[str]=["open"]):
        assert check_type_list(check_list, str)
        for x in check_list: assert x in ["open", "lock", "esql"]
        if self.con is not None:
            if "open" in check_list and self.is_closed():
                self.raise_error("connection is closed.", exception=CustomSQLException)
            if "lock" in check_list and len(self.sql_list) > 0:
                self.raise_error("sql_list is not empty. you can do after ExecuteSQL().", exception=CustomSQLException)
            if "esql" in check_list and len(self.sql_list) == 0:
                self.raise_error("sql_list is empty. you set executable sql.", exception=CustomSQLException)

    def display_sql(self, sql: str) -> str:
        assert isinstance(sql, str)
        return ("SQL:" + sql[:self.max_disp_len] + " ..." + sql[-self.max_disp_len:] if len(sql) > self.max_disp_len*2 else sql)

    @classmethod
    def get_colname_from_cursor(cls, description, dbtype: str):
        assert dbtype in DBTYPES
        if   dbtype == "psgre":
            return [x.name for x in description]
        elif dbtype == "mysql":
            return [x[0] for x in description]
    
    def select_sql(self, sql: str, ret_polars: bool=None) -> pd.DataFrame | pl.DataFrame:
        self.logger.info("START")
        assert isinstance(sql, str)
        assert ret_polars is None or isinstance(ret_polars, bool)
        self.check_status(["open","lock"])
        df  = pd.DataFrame()
        sql = sql.strip()
        ret_polars = self.use_polars if ret_polars is None else ret_polars
        if self.dbinfo["dbtype"] == "mysql":
            sql = escape_mysql_reserved_word(sql, RESERVED_WORD_MYSQL)
        if strfind(r"^select", sql, flags=re.IGNORECASE) == False:
            self.raise_error(f"sql: {sql[:100]}... is not started 'SELECT'", exception=CustomSQLException)
        self.logger.debug(f"SQL: {self.display_sql(sql)}")
        if self.dbinfo["dbtype"] in ["mongo"]:
            i_str, j_str = find_matching_words(sql, "select ", " from ", is_case_inensitive=True)
            assert i_str >= 0 and j_str >= 0
            str_select = sql[i_str:j_str].strip()
            if str_select == "*": str_select = None
            else: str_select = [x.strip() for x in str_select.split(",")]
            i_str, j_str = find_matching_words(sql, " from ", [" where ", " group by ", " having ", " limit ", ";"], is_case_inensitive=True)
            assert i_str >= 0
            str_from = sql[i_str:].strip() if j_str < 0 else sql[i_str:j_str].strip()
            i_str, j_str = find_matching_words(sql, " where ", [" group by ", " having ", " limit ", ";"], is_case_inensitive=True)
            if i_str >= 0:
                sql_where_clause = sql[i_str:j_str].strip() if j_str >= 0 else sql[i_str:].strip()
                mongo_filter     = sql_to_mongo_filter(sql_where_clause)
            else:
                mongo_filter = None
            i_str, j_str = find_matching_words(sql, " limit ", [";"], is_case_inensitive=True)
            if i_str >= 0:
                sql_limit_clause = sql[i_str:j_str].strip() if j_str >= 0 else sql[i_str:].strip()
                sql_limit_clause = int(sql_limit_clause)
            else:
                sql_limit_clause = None
            self.logger.info(f"table name: {str_from}, filter: {mongo_filter}, projection: {str_select}, limit: {sql_limit_clause}")
            if sql_limit_clause is not None:
                cursor = self.con.get_collection(str_from).find(filter=mongo_filter, projection=str_select).limit(sql_limit_clause)
            else:
                cursor = self.con.get_collection(str_from).find(filter=mongo_filter, projection=str_select)
            data = list(cursor)
            if len(data) == 0:
                if str_select is not None:
                    columns = str_select
                elif hasattr(self, "db_layout") and str_from in self.db_layout:
                    columns = self.db_layout[str_from]
                else:
                    columns = []
                if ret_polars:
                    df = pl.DataFrame([], schema=columns)
                else:
                    df = pd.DataFrame(columns=columns)
            else:
                if ret_polars:
                    df = pl.DataFrame(data, strict=False)
                else:
                    df = pd.DataFrame(data)
        elif self.dbinfo["dbtype"] in ["psgre", "mysql"] and self.con is not None:
            self.con.autocommit = True # Autocommit ON because even references are locked in principle.
            cur = self.con.cursor()
            cur.execute(sql)
            rows     = cur.fetchall()
            colnames = self.get_colname_from_cursor(cur.description, self.dbinfo["dbtype"])
            if ret_polars:
                if len(rows) == 0:
                    df = pl.DataFrame([], schema=colnames)
                else:
                    df = pl.DataFrame(rows, schema=colnames, orient="row")
            else:
                if len(rows) == 0:
                    df = pd.DataFrame(columns=colnames)
                else:
                    df = pd.DataFrame(rows, columns=colnames)
                df = drop_duplicate_columns(df)
            cur.close()
            self.con.autocommit = False
        for x in df.columns:
            if ret_polars:
                if self.dbinfo["dbtype"] in ["mysql", "mongo", "psgre"]:
                    """
                    Polars' datetime is converted to UTC datetime but the datetime after converted don't have "UTC" attribute.
                    >>> rows[:2]
                    [(1, datetime.datetime(2023, 1, 1, 19, 0, tzinfo=datetime.timezone(datetime.timedelta(seconds=32400))), datetime.datetime(2023, 1, 2, 9, 0, tzinfo=datetime.timezone(datetime.timedelta(seconds=32400))), 0, 42, 1.23, None, 'Hello', None, True, False, 'A'), (2, datetime.datetime(2023, 5, 6, 1, 30, tzinfo=datetime.timezone(datetime.timedelta(seconds=32400))), None, 100, None, 1e+20, 0.1, "123'ABC", "foo's bar", False, None, 'B')]
                    >>> pl.DataFrame(rows[:2], schema=colnames, orient="row")
                    shape: (2, 12)
                    ┌─────┬─────────────────────┬─────────────────────┬────────────┬───┬──────────────┬─────────────┬───────────────┬─────────────────┐
                    │ id  ┆ datetime_no_nan     ┆ datetime_with_nan   ┆ int_no_nan ┆ … ┆ str_with_nan ┆ bool_no_nan ┆ bool_with_nan ┆ category_column │
                    │ --- ┆ ---                 ┆ ---                 ┆ ---        ┆   ┆ ---          ┆ ---         ┆ ---           ┆ ---             │
                    │ i64 ┆ datetime[μs]        ┆ datetime[μs]        ┆ i64        ┆   ┆ str          ┆ bool        ┆ bool          ┆ str             │
                    ╞═════╪═════════════════════╪═════════════════════╪════════════╪═══╪══════════════╪═════════════╪═══════════════╪═════════════════╡
                    │ 1   ┆ 2023-01-01 10:00:00 ┆ 2023-01-02 00:00:00 ┆ 0          ┆ … ┆ null         ┆ true        ┆ false         ┆ A               │
                    │ 2   ┆ 2023-05-05 16:30:00 ┆ null                ┆ 100        ┆ … ┆ foo's bar    ┆ false       ┆ null          ┆ B               │
                    └─────┴─────────────────────┴─────────────────────┴────────────┴───┴──────────────┴─────────────┴───────────────┴─────────────────┘
                    """
                    if df.schema[x] == pl.Datetime:
                        df = df.with_columns(df[x].dt.convert_time_zone("UTC"))
            else:
                if self.dbinfo["dbtype"] in ["mysql", "mongo"]:
                    if pd.api.types.is_datetime64_any_dtype(df[x]):
                        df[x] = df[x].dt.tz_localize("UTC")
        self.logger.info("END")
        return df

    def set_sql(self, sql: list[str]):
        self.logger.info("START")
        assert isinstance(sql, str) or isinstance(sql, list)
        assert self.dbinfo["dbtype"] in ["psgre", "mysql"]
        if isinstance(sql, str): sql = [sql, ]
        for x in sql:
            if strfind(r"^select", x, flags=re.IGNORECASE):
                self.raise_error(self.display_sql(x) + ". you can't set 'SELECT' sql.", exception=CustomSQLException)
            else:
                if self.dbinfo["dbtype"] == "mysql":
                    x = escape_mysql_reserved_word(x, RESERVED_WORD_MYSQL)
                self.sql_list.append(x)
                self.logger.debug(f"SQL: {self.display_sql(x)}")
        self.logger.info("END")

    def execute_sql(self, sql: str=None):
        """ Execute the contents of sql_list. """
        self.logger.info("START")
        assert sql is None or isinstance(sql, str)
        if self.dbinfo["dbtype"] in ["mongo"]:
            self.logger.warning("Execute function is ignored in case dbtype is 'MongoDB'")
            self.logger.info("END")
            return None
        assert self.dbinfo["dbtype"] in ["psgre", "mysql"]
        results = None
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
            except Exception as e:
                self.con.rollback()
                cur.close()
                self.raise_error(f"SQL ERROR: {e.args}", exception=e)
            try:
                results = cur.fetchall()
            except psycopg2.ProgrammingError:
                results = None
            cur.close()
        self.sql_list = []
        self.logger.info("END")
        return results

    def read_table_layout(self, tblname: str=None) -> pd.DataFrame:
        self.logger.info("START")
        assert tblname is None or isinstance(tblname, str)
        if self.dbinfo["dbtype"] == "mongo":
            df = []
            for collection in self.con.list_collection_names():
                try:
                    data = self.con[collection].find_one()
                except pymongo.errors.OperationFailure:
                    data = None
                if data is None:
                    continue
                else:
                    dfwk = pd.DataFrame(list(data.keys()), columns=["colname"])
                    dfwk["tblname"] = collection
                    df.append(dfwk)
            if len(df) == 0:
                df = pd.DataFrame(columns=["tblname", "colname"])
            else:
                df = pd.concat(df, axis=0, ignore_index=True, sort=False)
        else:
            if   self.dbinfo["dbtype"] == "psgre":
                sql = f"SELECT table_name as tblname, column_name as colname, data_type as data_type FROM information_schema.columns where table_schema = 'public' "
            elif self.dbinfo["dbtype"] == "mysql":
                sql = f"SELECT table_name as tblname, column_name as colname, data_type as data_type FROM information_schema.columns where table_schema = '{self.dbinfo['dbname']}' "
            if tblname is not None: sql += f"and table_name = '{tblname}' "
            sql += "order by table_name, ordinal_position;"
            df = self.select_sql(sql, ret_polars=False)
        self.logger.info("END")
        return df
    
    def read_table_constraint(self, tblname: str=None) -> pd.DataFrame:
        self.logger.info("START")
        assert tblname is None or isinstance(tblname, str)
        if   self.dbinfo["dbtype"] == "psgre":
            sql = f"""
            SELECT ccu.table_name, ccu.constraint_name, ccu.column_name FROM information_schema.table_constraints tc
            INNER JOIN information_schema.constraint_column_usage ccu ON (
                tc.table_catalog=ccu.table_catalog
                and tc.table_schema=ccu.table_schema
                and tc.table_name=ccu.table_name
                and tc.constraint_name=ccu.constraint_name
            )
            WHERE
                tc.table_catalog='{self.dbinfo['dbname']}'
                and tc.table_schema='public'
                and tc.constraint_type='PRIMARY KEY'
            """.strip()
            if tblname is not None: sql += f" and tc.table_name = '{tblname}' "
            sql += ";"
        elif self.dbinfo["dbtype"] == "mysql":
            sql = f"""
            SELECT TABLE_NAME as table_name, COLUMN_NAME as column_name FROM information_schema.columns
            WHERE
                table_schema = '{self.dbinfo['dbname']}' and
                column_key   = 'PRI'
            """.strip()
            if tblname is not None: sql += f" and table_name = '{tblname}' "
            sql += " ORDER BY table_name, ordinal_position;"
        else:
            return pd.DataFrame(columns=["table_name", "column_name"])
        df = self.select_sql(sql, ret_polars=False)
        self.logger.info("END")
        return df

    def execute_copy_from_df(
        self, df: pd.DataFrame | pl.DataFrame, tblname: str, system_colname_list: list[str] = ["sys_updated"], 
        filename: str=None, encoding: str="utf8", n_round: int=8, 
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
        if self.dbinfo["dbtype"] not in ["psgre"]:
            self.raise_error("COPY command is only for PostgreSQL", exception=CustomSQLException)
        if self.use_polars:
            assert isinstance(df, pl.DataFrame)
            df = df.to_pandas()
        else:
            assert isinstance(df, pd.DataFrame)
        assert isinstance(tblname, str)
        assert check_type_list(system_colname_list, str)
        if filename is None:
            filename = f"./postgresql_copy.{str(id(self.con))}.csv"
        assert isinstance(filename, str)
        assert isinstance(encoding, str)
        assert isinstance(check_columns, bool)
        self.check_status(["open", "lock"])
        columns = [x for x in self.db_layout.get(tblname) if x not in system_colname_list] if self.db_layout.get(tblname) is not None else []
        ndf     = np.isin(columns, df.columns.values)
        if check_columns:
            if (ndf == False).sum() > 0:
                self.raise_error(f'{np.array(columns)[~ndf]} columns must be added in df: {df}.', exception=CustomSQLException)
            df = df.loc[:, columns].copy()
        else:
            # Create a column that does not exist in the table columns.
            df = df.loc[:, np.array(columns)[ndf]].copy()
            for x in np.array(columns)[~ndf]: df[x] = float("nan")
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
            except Exception as e:
                self.con.rollback() # Not sure if this code is needed.
                cur.close()
                self.raise_error("csv copy error !!", exception=e)
        self.logger.info("END")
        return df

    def convert_df_for_dbtype(self, df: pd.DataFrame | pl.DataFrame, tblname: str) -> pd.DataFrame | pl.DataFrame:
        if isinstance(df, pl.DataFrame):
            use_polars = True
            df = df.fill_nan(None)
        else:
            assert isinstance(df, pd.DataFrame)
            use_polars = False
        if self.dbinfo["dbtype"] in ["psgre", "mysql"]:
            for x in df.columns:
                # convert to datetime
                if x in list(self.db_layout_type[tblname].keys()) and self.db_layout_type[tblname][x] in ["datetime", "timestamp with time zone"]:
                    if use_polars:
                        if self.dbinfo["dbtype"] == "mysql":
                            df = df.with_columns(pl.col(x).dt.strftime("%Y-%m-%d %H:%M:%S.%f"))
                        else:
                            df = df.with_columns(pl.col(x).dt.strftime("%Y-%m-%d %H:%M:%S.%f%z"))
                    else:
                        df[x] = pd.to_datetime(df[x], utc=True)
                        if self.dbinfo["dbtype"] == "mysql":
                            df[x] = df[x].dt.strftime("%Y-%m-%d %H:%M:%S.%f") # MySQL doesn't manage TimeZone so convert all data to UTC datetime.
                        else:
                            df[x] = df[x].dt.strftime("%Y-%m-%d %H:%M:%S.%f%z")
                if use_polars:
                    if df.schema[x] == pl.Utf8:
                        if self.dbinfo["dbtype"] in ["psgre", "mysql"]:
                            df = df.with_columns(pl.col(x).str.replace("'", "''", n=-1))
                        if self.dbinfo["dbtype"] in ["mysql"]:
                            df = df.with_columns(pl.col(x).str.replace(r"\\", "\\\\", n=-1))
                else:
                    if isinstance(df[x].dtype, object):
                        if self.dbinfo["dbtype"] in ["psgre", "mysql"]:
                            df[x] = df[x].replace("'", "''", regex=True) # To escape "'", make it double quotation
                        if self.dbinfo["dbtype"] in ["mysql"]:
                            if hasattr(df[x], "str"):
                                df[x] = df[x].str.replace("\\", "\\\\")
        return df

    def insert_from_df(
        self, df: pd.DataFrame | pl.DataFrame, tblname: str, 
        set_sql: bool=True, n_round: int=8, str_null :str="%%null%%", is_select: bool=False, n_jobs: int=1
    ):
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
        self.logger.info("START")
        if self.use_polars:
            assert isinstance(df, pl.DataFrame)
        else:
            assert isinstance(df, pd.DataFrame)
            df = df.copy()
        assert isinstance(tblname, str)
        assert isinstance(set_sql, bool)
        if self.dbinfo["dbtype"] in ["mongo"]:
            if self.use_polars:
                data = df.to_dicts()
            else:
                for x in df.columns:
                    if pd.api.types.is_datetime64_any_dtype(df[x]):
                        df[x] = df[x].replace({pd.NaT: None})
                data = df.to_dict(orient='records')
            result = self.con.get_collection(tblname).insert_many(data, ordered=False) # https://www.mongodb.com/ja-jp/docs/manual/core/timeseries/timeseries-best-practices/
            self.logger.info(f"{str(result)[:self.max_disp_len]} ...")
        elif self.dbinfo["dbtype"] in ["psgre", "mysql"]:
            if is_select:
                columns = self.db_layout.get(tblname) if self.db_layout.get(tblname) is not None else []
                if self.use_polars:
                    df = df.select([x for x in df.columns if x in columns])
                else:
                    df = df.loc[:, df.columns.isin(columns)].copy()
            df   = self.convert_df_for_dbtype(df, tblname)
            cols = [f"`{x}`" if x in RESERVED_WORD_MYSQL else x for x in df.columns] if self.dbinfo["dbtype"] == "mysql" else list(df.columns)
            sql  = "insert into " + tblname + " (" + ",".join(cols) + ") values "
            if self.use_polars:
                se = df.map_rows(lambda x: str(x).replace(", ", ","), return_dtype=pl.Utf8)["map"].str.replace_many(
                    [",None,", ",None)", "(None,", ",True,", ",True)", "(True,", ",False,", ",False)", "(False,", ": True,", ": True}", ": False,", ": False}"],
                    [",null,", ",null)", "(null,", ",true,", ",true)", "(true,", ",false,", ",false)", "(false,", ": true,", ": true}", ": false,", ": false}"]
                ).str.replace_many([",None,", ",None)", "(None,"], [",null,", ",null)", "(null,"]) # Consider this patter ,None,None,None, ( -> ,null,None,null, at first process done) 
                sql += ",".join(se.to_list())
                sql += ";"
            else:
                df = to_string_all_columns(df, n_round=n_round, rep_nan=str_null, rep_inf=str_null, rep_minf=str_null, strtmp="-9999999", n_jobs=n_jobs)
                for ndf in df.values:
                    sql += "('" + "','".join(ndf.tolist()) + "'), "
                sql = sql[:-2] + ";"
                sql = sql.replace("'"+str_null+"'", "null")
            if set_sql:
                self.set_sql(sql)
            else:
                self.execute_sql(sql)
        self.logger.info("END")
    
    def update_from_df(
        self, df: pd.DataFrame | pl.DataFrame, tblname: str, columns_set: list[str], columns_where: list[str],
        set_sql: bool=True, n_round: int=8, str_null :str="%%null%%", n_jobs: int=1
    ):
        self.logger.info("START")
        if self.use_polars:
            assert isinstance(df, pl.DataFrame)
            df = df.to_pandas()
        else:
            assert isinstance(df, pd.DataFrame)
            df = df.copy()
        assert isinstance(tblname, str)
        assert isinstance(set_sql, bool)
        assert check_type_list(columns_set,   str)
        assert check_type_list(columns_where, str)
        assert self.dbinfo["dbtype"] in ["psgre", "mysql"]
        df    = self.convert_df_for_dbtype(df, tblname)
        df    = to_string_all_columns(df, n_round=n_round, rep_nan=str_null, rep_inf=str_null, rep_minf=str_null, strtmp="-9999999", n_jobs=n_jobs)
        sql   = ""
        cols1 = [f"`{x}`" if x in RESERVED_WORD_MYSQL else x for x in columns_set  ] if self.dbinfo["dbtype"] == "mysql" else columns_set
        cols2 = [f"`{x}`" if x in RESERVED_WORD_MYSQL else x for x in columns_where] if self.dbinfo["dbtype"] == "mysql" else columns_where
        for i in range(df.shape[0]):
            sql += (
                f"update {tblname} set " + ", ".join([f"{x} = '{df[y].iloc[i]}'" for x, y in zip(cols1, columns_set)]) + 
                " where " +             " and ".join([f"{x} = '{df[y].iloc[i]}'" for x, y in zip(cols2, columns_set)]) + ";"
            )
        sql = sql.replace("'"+str_null+"'", "null")
        if set_sql:
            self.set_sql(sql)
        else:
            self.execute_sql(sql)
        self.logger.info("END")

    def delete_sql(self, tblname: str, str_where: str=None, set_sql: bool=True):
        self.logger.info("START")
        assert isinstance(tblname, str)
        assert str_where is None or isinstance(str_where, str)
        assert isinstance(set_sql, bool)
        if isinstance(str_where, str):
            assert strfind(r"^where ", str_where.lower()) == False
        if self.dbinfo["dbtype"] in ["psgre", "mysql"]:
            sql = f"DELETE FROM {tblname}"
            if str_where is not None:
                sql += f" WHERE {str_where}"
            sql += ";"
            if set_sql:
                self.set_sql(sql)
            else:
                self.execute_sql(sql)
        elif self.dbinfo["dbtype"] in ["mongo"]:
            filter = sql_to_mongo_filter(str_where.strip()) if str_where is not None else {}
            self.logger.info(f"table name: {tblname}, filter: {filter}")
            result = self.con.get_collection(tblname).delete_many(filter=filter)
            self.logger.info(f"{result}")
        self.logger.info("END")
