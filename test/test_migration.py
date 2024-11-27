import argparse, datetime
# local package
from kkpsgre.psgre import DBConnector
from kkpsgre.migration import migrate
from kklogger import set_logger

LOGGER = set_logger(__name__)


HOST_FR   = "127.0.0.1"
PORT_FR   = 3306
USER_FR   = "mysql"
PASS_FR   = "mysql"
DBNAME_FR = "test"
DBTYPE_FR = "mysql"


HOST_TO   = "127.0.0.1"
PORT_TO   = 5432
USER_TO   = "postgres"
PASS_TO   = "postgres"
DBNAME_TO = "test"
DBTYPE_TO = "psgre"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tbl", type=str, help="table name")
    parser.add_argument("--num", type=int, default=10000)
    parser.add_argument("--fr",  type=lambda x: datetime.datetime.strptime(x, "%Y%m%d"))
    parser.add_argument("--to",  type=lambda x: datetime.datetime.strptime(x, "%Y%m%d"))
    parser.add_argument("--pkey", type=lambda x: x.split(","))
    parser.add_argument("--update",  action='store_true', default=False)
    parser.add_argument("--isnoerr", action='store_true', default=False)
    args = parser.parse_args()
    print(args)
    DB_from = DBConnector(HOST_FR, PORT_FR, DBNAME_FR, USER_FR, PASS_FR, dbtype=DBTYPE_FR, max_disp_len=200)
    DB_to   = DBConnector(HOST_TO, PORT_TO, DBNAME_TO, USER_TO, PASS_TO, dbtype=DBTYPE_TO, max_disp_len=200)
    df_from, df_exist, df_insert = migrate(
        DB_from, DB_to, args.tbl, f"unixtime >= {int(args.fr.timestamp())} and unixtime < {int(args.to.timestamp())}",
        str_where_to=f"unixtime >= '{args.fr.strftime('%Y-%m-%d %H:%M:%S.%f%z')}' and unixtime < '{args.to.strftime('%Y-%m-%d %H:%M:%S.%f%z')}'",
        func_convert=lambda df: df, # If you want to add.
        pkeys=args.pkey, n_split=args.num, is_no_error_when_different=args.isnoerr, is_delete=False, is_update=args.update
    )

