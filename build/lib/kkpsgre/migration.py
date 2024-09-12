import numpy as np
import pandas as pd
from tqdm import tqdm
# local package
from kkpsgre.psgre import DBConnector
from kkpsgre.util.com import check_type, check_type_list
from kkpsgre.util.logger import set_logger
LOGGER = set_logger(__name__)


__all__ = [
    "migrate"
]


def create_multi_condition(idxs: pd.DataFrame | pd.MultiIndex):
    sql = None
    def __check(x):
        if check_type(x, [int, str, np.int8, np.int16, np.int32, np.int64]):
            return x
        else:
            LOGGER.raise_error(f"type: {type(x)}, {x} is not expected !!")
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
        LOGGER.raise_error(f"input data type is not expected. {type(idxs)}")
    return sql


def migrate(
    DB_from: DBConnector, DB_to: DBConnector, tblanme: str, str_where: str, pkeys: list[str]=None, n_split: int=10000,
    is_error_when_different: bool=True, is_delete: bool=False, is_update: bool=False
):
    assert isinstance(DB_from, DBConnector) and DB_from.is_closed() == False
    assert isinstance(DB_to,   DBConnector) and DB_to.  is_closed() == False
    assert isinstance(tblanme, str) and tblanme in DB_from.db_layout and tblanme in DB_to.db_layout
    if pkeys is None:
        assert tblanme in DB_from.db_constraint
        assert tblanme in DB_to.  db_constraint
        pkeys = DB_from.db_constraint[tblanme].copy()
        assert pkeys == DB_to.db_constraint[tblanme]
    else:
        assert isinstance(pkeys, list) and len(pkeys) > 0 and check_type_list(pkeys, str)
        if tblanme in DB_from.db_constraint:
            for pkey in DB_from.db_constraint[tblanme]:
                assert pkey in pkeys
        if tblanme in DB_to.db_constraint:
            for pkey in DB_to.db_constraint[tblanme]:
                assert pkey in pkeys
    assert str_where is None or isinstance(str_where, str)
    assert n_split   is None or (isinstance(n_split, int) and n_split > 0)
    assert isinstance(is_error_when_different, bool)
    assert isinstance(is_delete, bool)
    assert isinstance(is_update, bool)
    LOGGER.info(f"DB FROM: {DB_from.dbinfo}", color=["BOLD", "GREEN"])
    LOGGER.info(f"DB TO:   {DB_to.  dbinfo}", color=["BOLD", "GREEN"])
    cols_from = DB_from.db_layout[tblanme]
    cols_to   = DB_to.  db_layout[tblanme]
    cols_com  = [x for x in cols_from if x in cols_to]
    LOGGER.info(f"Table name: {tblanme}, columns common: {cols_com}")
    cols_dfr  = [x for x in cols_from if x not in cols_com]
    cols_dto  = [x for x in cols_to   if x not in cols_com]
    if len(cols_dfr) > 0: LOGGER.warning(f"Some columns doesn't exist in DB FROM: {cols_dfr}")
    if len(cols_dto) > 0: LOGGER.warning(f"Some columns doesn't exist in DB FROM: {cols_dto}")
    if is_error_when_different and len(cols_dfr) > 0: LOGGER.raise_error("Stop process due to different columns.")
    if is_error_when_different and len(cols_dto) > 0: LOGGER.raise_error("Stop process due to different columns.")
    sql      = ("SELECT " + ", ".join(pkeys) + f" FROM {tblanme}") + (";" if str_where is None else f" WHERE {str_where};")
    LOGGER.info(f"Primary key select. SQL: {sql}")
    df_from  = DB_from.select_sql(sql)
    df_exist = DB_to.  select_sql(sql)
    LOGGER.info(f"Data FROM: {df_from.shape}, TO: {df_exist.shape}")
    df_from  = df_from. groupby(pkeys).size().reset_index().set_index(pkeys) # It might be duplicated when primary key is not set to the table.
    df_exist = df_exist.groupby(pkeys).size().reset_index().set_index(pkeys) # It might be duplicated when primary key is not set to the table.
    df_exist["__work"] = 1
    df_from["__work"]  = df_exist["__work"]
    n_dupl   = (~df_from["__work"].isna()).sum()
    LOGGER.info(f"Data duplicated: {n_dupl}")
    if is_delete == False:
        df_from = df_from.loc[df_from["__work"].isna()]
    if n_split is None or n_split > df_from.shape[0]: n_split = df_from.shape[0]
    df_insert = None
    if df_from.shape[0] > 0:
        if n_dupl == 0:
            # Nothing in DB_to
            df_insert = DB_from.select_sql((f"SELECT " + ", ".join(cols_com) + f" FROM {tblanme}") + (";" if str_where is None else f" WHERE {str_where};"))
            if is_update:
                list_idx  = np.array_split(np.arange(df_insert.shape[0]), df_insert.shape[0] // n_split)
                for idxs in tqdm(list_idx):
                    if is_delete:
                        DB_to.set_sql(f"DELETE FROM {tblanme} WHERE {create_multi_condition(df_insert.iloc[idxs][pkeys])}")
                    DB_to.insert_from_df(df_insert.iloc[idxs], tblanme, set_sql=True)
                    DB_to.execute_sql()
        else:
            # Some data is duplicated in DB_TO.
            list_idx = np.array_split(np.arange(df_from.shape[0]), df_from.shape[0] // n_split)
            for idxs in tqdm(list_idx):
                index     = df_from.index[idxs].copy()
                df_insert = DB_from.select_sql(
                    f"SELECT " + ", ".join(cols_com) + f" FROM {tblanme} WHERE {create_multi_condition(index)}"
                )
                if is_update:
                    if is_delete:
                        DB_to.set_sql(f"DELETE FROM {tblanme} WHERE {create_multi_condition(df_insert[pkeys])}")
                    DB_to.insert_from_df(df_insert, tblanme, set_sql=True)
                    DB_to.execute_sql()
    else:
        LOGGER.info("No candidate to be inserted. All data is duplicated or nothing.")
    return df_from, df_exist, df_insert