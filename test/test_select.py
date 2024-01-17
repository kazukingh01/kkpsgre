from kkpsgre.psgre import Psgre


if __name__ == "__main__":

    con = Psgre("host=172.18.10.2 port=5432 dbname=testdb user=postgres password=postgres")
    df  = con.select_sql("select * from test;")
    print(df)