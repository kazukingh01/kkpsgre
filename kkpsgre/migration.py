import copy
import numpy as np
import pandas as pd
from tqdm import tqdm
# local package
from kkpsgre.psgre import DBConnector
from kkpsgre.util.sql import create_multi_condition
from kkpsgre.util.com import check_type_list
from kklogger import set_logger


LOGGER = set_logger(__name__)


__all__ = [
    "migrate"
]


def migrate(
    DB_from: DBConnector, DB_to: DBConnector, tblanme: str, str_where: str, pkeys: list[str]=None,
    str_where_to: str=None, func_convert=None, n_split: int=10000, 
    is_no_error_when_different: bool=False, is_delete: bool=False, is_update: bool=False
):
    LOGGER.info("START")
    assert isinstance(DB_from, DBConnector) and DB_from.is_closed() == False and DB_from.dbinfo["dbtype"] in ["psgre", "mysql"]
    assert isinstance(DB_to,   DBConnector) and DB_to.  is_closed() == False and DB_to  .dbinfo["dbtype"] in ["psgre", "mysql", "mongo"]
    assert isinstance(tblanme, str) and tblanme in DB_from.db_layout and tblanme in DB_to.db_layout
    if pkeys is None:
        assert tblanme in DB_from.db_constraint
        assert tblanme in DB_to.  db_constraint
        pkeys = DB_from.db_constraint[tblanme].copy()
        if DB_to.dbinfo["dbtype"] in ["psgre", "mysql"]:
            assert pkeys == DB_to.db_constraint[tblanme]
        else:
            LOGGER.warning(f'DB type: {DB_to.dbinfo["dbtype"]} cannot check constraint !!')
    else:
        assert isinstance(pkeys, list) and len(pkeys) > 0 and check_type_list(pkeys, str)
        if tblanme in DB_from.db_constraint:
            for pkey in DB_from.db_constraint[tblanme]:
                assert pkey in pkeys
        if tblanme in DB_to.db_constraint:
            if DB_to.dbinfo["dbtype"] in ["psgre", "mysql"]:
                for pkey in DB_to.db_constraint[tblanme]:
                    assert pkey in pkeys
            else:
                LOGGER.warning(f'DB type: {DB_to.dbinfo["dbtype"]} cannot check constraint !!')
    assert str_where    is None or isinstance(str_where,    str)
    assert str_where_to is None or isinstance(str_where_to, str)
    if str_where_to is None: str_where_to = str_where
    if func_convert is None: func_convert = lambda x: x
    assert n_split   is None or (isinstance(n_split, int) and n_split > 0)
    assert isinstance(is_no_error_when_different, bool)
    assert isinstance(is_delete, bool)
    assert isinstance(is_update, bool)
    LOGGER.info(f"DB FROM: {DB_from.dbinfo}", color=["BOLD", "GREEN"])
    LOGGER.info(f"DB TO:   {DB_to.  dbinfo}", color=["BOLD", "GREEN"])
    cols_from = DB_from.db_layout[tblanme]
    cols_to   = DB_to.  db_layout[tblanme] if DB_to.dbinfo["dbtype"] in ["psgre", "mysql"] else copy.deepcopy(cols_from)
    cols_com  = [x for x in cols_from if x in cols_to]
    LOGGER.info(f"Table name: {tblanme}, columns common: {cols_com}")
    cols_dfr  = [x for x in cols_from if x not in cols_com]
    cols_dto  = [x for x in cols_to   if x not in cols_com]
    if len(cols_dfr) > 0: LOGGER.warning(f"Some columns doesn't exist in DB FROM: {cols_dfr}")
    if len(cols_dto) > 0: LOGGER.warning(f"Some columns doesn't exist in DB TO  : {cols_dto}")
    if (is_no_error_when_different == False) and len(cols_dfr) > 0: LOGGER.raise_error("Stop process due to different columns.")
    if (is_no_error_when_different == False) and len(cols_dto) > 0: LOGGER.raise_error("Stop process due to different columns.")
    sql_fr   = ("SELECT " + ", ".join(pkeys) + f" FROM {tblanme}") + (";" if str_where    is None else f" WHERE {str_where   };")
    sql_to   = ("SELECT " + ", ".join(pkeys) + f" FROM {tblanme}") + (";" if str_where_to is None else f" WHERE {str_where_to};")
    LOGGER.info(f"Primary key select. SQL FROM: {sql_fr}")
    if str_where_to is not None: LOGGER.info(f"Primary key select. SQL TO  : {sql_to}")
    df_from  = DB_from.select_sql(sql_fr)
    df_exist = DB_to.  select_sql(sql_to)
    df_from[ "__id"] = df_from. index.copy()
    df_exist["__id"] = df_exist.index.copy()
    LOGGER.info(f"Data FROM: {df_from .shape}\n{df_from }")
    LOGGER.info(f"Data TO  : {df_exist.shape}\n{df_exist}")
    dfwk     = func_convert(df_from.copy())
    dfwk     = dfwk.    groupby(pkeys)[["__id"]].first().reset_index().set_index(pkeys) # It might be duplicated when primary key is not set to the table.
    df_exist = df_exist.groupby(pkeys)[["__id"]].first().reset_index().set_index(pkeys) # It might be duplicated when primary key is not set to the table.
    df_exist["__work"] = 1
    dfwk[    "__work"] = df_exist["__work"]
    n_dupl   = (~dfwk["__work"].isna()).sum()
    LOGGER.info(f"Data duplicated: {n_dupl}")
    if is_delete == False:
        dfwk    = dfwk.loc[dfwk["__work"].isna()]
        df_from = df_from.loc[dfwk["__id"].values].set_index(pkeys)
    else:
        df_from = df_from.groupby(pkeys)[["__id"]].first().reset_index().set_index(pkeys)
    df_insert = None
    if df_from.shape[0] > 0:
        if n_dupl == 0:
            # Nothing in DB_to
            df_insert = DB_from.select_sql((f"SELECT " + ", ".join(cols_com) + f" FROM {tblanme}") + (";" if str_where is None else f" WHERE {str_where};"))
            df_insert = func_convert(df_insert)
            if n_split is None or n_split > df_insert.shape[0]: n_split = df_insert.shape[0]
            if is_update:
                list_idx = np.array_split(np.arange(df_insert.shape[0]), df_insert.shape[0] // n_split)
                for idxs in tqdm(list_idx):
                    if is_delete:
                        DB_to.delete_sql(tblanme, str_where=(("" if str_where_to is None else f"{str_where_to} AND ") + f"{create_multi_condition(df_insert.iloc[idxs][pkeys])}"), set_sql=True)
                    DB_to.insert_from_df(df_insert.iloc[idxs], tblanme, set_sql=True)
                    DB_to.execute_sql()
        else:
            # Some data is duplicated in DB_TO.
            if n_split is None or n_split > df_from.shape[0]: n_split = df_from.shape[0]
            list_idx = np.array_split(np.arange(df_from.shape[0]), df_from.shape[0] // n_split)
            for idxs in tqdm(list_idx):
                index     = df_from.index[idxs].copy()
                df_insert = DB_from.select_sql(f"SELECT " + ", ".join(cols_com) + f" FROM {tblanme} WHERE " + ("" if str_where is None else f"{str_where} AND ") + f"{create_multi_condition(index)};")
                df_insert = func_convert(df_insert)
                if is_update:
                    if is_delete:
                        DB_to.delete_sql(tblanme, ("" if str_where_to is None else f"{str_where_to} AND ") + f"{create_multi_condition(df_insert[pkeys])}")
                    DB_to.insert_from_df(df_insert, tblanme, set_sql=True)
                    DB_to.execute_sql()
    else:
        LOGGER.info("No candidate to be inserted. All data is duplicated or nothing.")
    LOGGER.info("END")
    return df_from, df_exist, df_insert