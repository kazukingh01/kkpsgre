#! /bin/sh
set -euo pipefail

python test_sql_pandas.py
python test_sql_polars.py
python test_error.py
