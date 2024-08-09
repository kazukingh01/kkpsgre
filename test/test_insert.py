import time
from kkpsgre.psgre import DBConnector
import pandas as pd
from dbconfig import HOST, PORT, DBNAME, USER, PASSWORD, DBTYPE


if __name__ == "__main__":
    con = DBConnector(HOST, PORT, DBNAME, USER, PASSWORD, dbtype=DBTYPE)
    df  = pd.DataFrame([1,2,3,4,5], columns=["test_id"])
    df["test_0"] = 2
    df["test_1"] = 1.1111
    df["test_2"] = 3.3444444444444443333333333
    df["test_3"] = "あいうえおかきくけこさしすせそたちつてと"
    df["test_4"] = "ああああああああああああああああああああああああああああああああああああああああああああああああああ"
    df.loc[2, df.columns[1:]] = float("nan")
    # insert
    con.set_sql("delete from test;")
    con.insert_from_df(df, "test", n_round=10, is_select=True)
    con.execute_sql()
    print(con.select_sql("select * from test;"))
    # update
    time.sleep(5) # test for sys_updated column.
    df.loc[df["test_id"] == 5, "test_4"] = "いいいいいいいいい"
    con.update_from_df(df.loc[df["test_id"] == 5], "test", ["test_4"], ["test_id"], set_sql=True)
    con.execute_sql()
    print(con.select_sql("select * from test;"))
    # update ( rollback ) 
    df.loc[df["test_id"] == 4, "test_4"] = "ううううううううう"
    con.update_from_df(df.loc[df["test_id"] == 4], "test", ["test_4"], ["test_id"], set_sql=True)
    con.set_sql("UPDATE test SET test_id = null;")
    try: con.execute_sql()
    except: con = DBConnector(HOST, PORT, DBNAME, USER, PASSWORD, dbtype=DBTYPE)
    print(con.select_sql("select * from test;"))
    # copy
    if DBTYPE == "psgre":
        con.set_sql("delete from test;")
        con.execute_sql()
        con.execute_copy_from_df(df, "test", n_round=10, check_columns=True)
