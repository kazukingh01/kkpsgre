from kkpsgre.psgre import Psgre
import pandas as pd


if __name__ == "__main__":

    con = Psgre("host=172.18.10.2 port=5432 dbname=testdb user=postgres password=postgres")
    df  = pd.DataFrame([1,2,3,4,5], columns=["test_id"])
    df["test_0"] = 2
    df["test_1"] = 1.1111
    df["test_2"] = 3.3444444444444443333333333
    df["test_3"] = "あいうえおかきくけこさしすせそたちつてと"
    # copy
    try:
        con.set_sql("delete from test;")
        con.execute_sql()
        con.execute_copy_from_df(df, "test", n_round=10, check_columns=True)
    except Exception as e:
        con = Psgre("host=172.18.10.2 port=5432 dbname=testdb user=postgres password=postgres")
        con.execute_copy_from_df(df, "test", n_round=10, check_columns=False)
    # insert
    df["test_4"] = "ああああああああああああああああああああああああああああああああああああああああああああああああああ"
    df["test_5"] = float("nan")
    df.loc[2, df.columns[1:]] = float("nan")
    try:
        con.set_sql("delete from test;")
        con.insert_from_df(df, "test", n_round=10, is_select=False)
        con.execute_sql()
    except Exception as e:
        con = Psgre("host=172.18.10.2 port=5432 dbname=testdb user=postgres password=postgres")
        con.set_sql("delete from test;")
        con.insert_from_df(df.iloc[:, :-1], "test", n_round=10, is_select=False)
        con.execute_sql()
