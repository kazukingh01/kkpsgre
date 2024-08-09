from kkpsgre.psgre import DBConnector
from dbconfig import HOST, PORT, DBNAME, USER, PASSWORD, DBTYPE


if __name__ == "__main__":
    con = DBConnector(HOST, PORT, DBNAME, USER, PASSWORD, dbtype=DBTYPE)
    df  = con.select_sql("select * from test;")
    print(df)