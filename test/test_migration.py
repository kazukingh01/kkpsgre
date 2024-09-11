import argparse, datetime
# local package
from kkpsgre.psgre import DBConnector
from kkpsgre.migration import migrate
from kkpsgre.util.logger import set_logger

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
    parser.add_argument("--pkey", type=lambda x: x.split(","), default="id")
    parser.add_argument("--update", action='store_true', default=False)
    args = parser.parse_args()
    print(args)
    DB_to   = DBConnector(HOST_FR, PORT_FR, DBNAME_FR, USER_FR, PASS_FR, dbtype=DBTYPE_FR, max_disp_len=200)
    DB_from = DBConnector(HOST_TO, PORT_TO, DBNAME_TO, USER_TO, PASS_TO, dbtype=DBTYPE_TO, max_disp_len=200)
    migrate(
        DB_from, DB_to, args.tbl, f"unixtime >= {int(datetime.datetime(2024,1,1,12,0,0).timestamp())} and unixtime <= {int(datetime.datetime(2024,1,1,13,0,0).timestamp())}",
        pkeys=args.pkey, n_split=args.num, is_error_when_different=True, is_delete=False, is_update=args.update
    )
