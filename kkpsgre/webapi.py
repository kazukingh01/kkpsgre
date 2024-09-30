import asyncio, copy
from fastapi import FastAPI
import pandas as pd
import numpy as np
from pydantic import BaseModel
# local package
from kkpsgre.psgre import DBConnector
from kkpsgre.util.sql import to_str_timestamp


class Select(BaseModel):
    sql: str

class Insert(BaseModel):
    data: dict
    tblname: str
    is_select: bool
    add_sql: str | None = None
        
class Delete(BaseModel):
    tblname: str
    str_where: str | None = None

class Exec(BaseModel):
    sql: str | list[str]

class ReConnect(BaseModel):
    logfilepath: str=""
    log_level: str="info"
    is_newlogfile: bool=False


def create_app(HOST: str, PORT: int, DBNAME: str, USER: str, PASS: str, DBTYPE: str):
    """
    Usage::
        webapi.py
        >>> from kkpsgre.webapi import create_app
        >>> app = create_app(HOST, PORT, DBNAME, USER, PASS, dbtype=DBTYPE)
        uvicorn
        >>> nohup uvicorn dbapi:app --port ${PORT} >/dev/null 2>&1 &

    """
    app  = FastAPI()
    lock = asyncio.Lock()
    DB   = DBConnector(HOST, PORT, DBNAME, USER, PASS, dbtype=DBTYPE, max_disp_len=200)

    @app.post('/select/')
    async def select(select: Select):
        async with lock:
            df = DB.select_sql(select.sql)
        return to_str_timestamp(df).to_json()

    @app.post('/insert/')
    async def insert(insert: Insert):
        df = pd.DataFrame(insert.data)
        for x in df.columns:
            if (df[x].dtype == np.dtypes.ObjectDType) and df.shape[0] > 0:
                if str(df[x].iloc[0]).find("%DATETIME%") == 0:
                    df[x] = df[x].str[len("%DATETIME%"):]
                    df[x] = pd.to_datetime(df[x])
        async with lock:
            if insert.add_sql is not None:
                DB.delete_sql(insert.tblname, str_where=insert.add_sql, set_sql=True)
            DB.insert_from_df(df, insert.tblname, set_sql=True, str_null="", is_select=insert.is_select)
            DB.execute_sql()
        return True

    @app.post('/delete/')
    async def delete(delete: Delete):
        async with lock:
            DB.delete_sql(delete.tblname, str_where=delete.str_where, set_sql=True)
            DB.execute_sql()
        return True

    @app.post('/exec/')
    async def exec(exec: Exec):
        async with lock:
            DB.set_sql(exec.sql)
            DB.execute_sql()
        return True

    @app.post('/reconnect/')
    async def connect(reconnect: ReConnect):
        if reconnect.logfilepath == "": reconnect.logfilepath = None
        async with lock:
            DB.__del__()
            DB.__init__(HOST, PORT, DBNAME, USER, PASS, dbtype=DBTYPE, max_disp_len=200, logfilepath=reconnect.logfilepath, log_level=reconnect.log_level, is_newlogfile=reconnect.is_newlogfile)
        return True

    @app.post('/disconnect/')
    async def disconnect(disconnect: BaseModel):
        async with lock:
            DB.__del__()
        return True

    @app.post('/dbinfo/')
    async def dbinfo(_: BaseModel):
        dictwk = None
        async with lock:
            dictwk = copy.deepcopy(DB.dbinfo)
        return dictwk

    @app.post('/test/')
    async def test(_: BaseModel):
        async with lock:
            df = DB.read_table_layout()
        return df.to_json()

    return app


"""
import argparse, requests, json, datetime
import pandas as pd
# local package
from kkpsgre.psgre import DBConnector
from kkpsgre.webapi import create_app
from xxxxxxx.config.psgre import HOST, PORT, DBNAME, USER, PASS, DBTYPE

app  = create_app(HOST, PORT, DBNAME, USER, PASS, DBTYPE)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reconnect",     action='store_true', default=False)
    parser.add_argument("--logfilepath",   type=str, default="")
    parser.add_argument("--log_level",     type=str, default="info")
    parser.add_argument("--ip",            type=str, default="127.0.0.1")
    parser.add_argument("--port",          type=int, default=8000)
    parser.add_argument("--is_newlogfile", action='store_true', default=False)
    parser.add_argument("--disconnect",    action='store_true', default=False)
    parser.add_argument("--test",          action='store_true', default=False)
    parser.add_argument("--check",         action='store_true', default=False)
    parser.add_argument("--db",            action='store_true', default=False)
    args   = parser.parse_args()
    def manual_connect(args):
        res = requests.post(f"http://{args.ip}:{args.port}/reconnect", json={"logfilepath": args.logfilepath, "log_level": args.log_level, "is_newlogfile": args.is_newlogfile}, headers={'Content-type': 'application/json'})
        return res
    if   args.reconnect:
        res = manual_connect(args)
        print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} status_code: {res.status_code}")
    elif args.disconnect:
        res = requests.post(f"http://{args.ip}:{args.port}/disconnect", json={}, headers={'Content-type': 'application/json'})
        print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} status_code: {res.status_code}")
    elif args.test:
        res = requests.post(f"http://{args.ip}:{args.port}/dbinfo", json={}, headers={'Content-type': 'application/json'})
        print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} status_code: {res.status_code}.")
        print(res.text)
        res = requests.post(f"http://{args.ip}:{args.port}/test", json={}, headers={'Content-type': 'application/json'})
        print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} status_code: {res.status_code}.")
        print(pd.DataFrame(json.loads(res.json())))
    elif args.check:
        res = requests.post(f"http://{args.ip}:{args.port}/test", json={}, headers={'Content-type': 'application/json'})
        if res.status_code != 200:
            print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} try to reconnect... [1]")
            res = manual_connect(args)
            print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} status_code: {res.status_code}.")
        else:
            df = pd.DataFrame(json.loads(res.json()))
            if df.shape[0] == 0:
                print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} try to reconnect... [2]")
                res = manual_connect(args)
                print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} status_code: {res.status_code}.")
            else:
                print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} status is fine. status_code: {res.status_code}.")
    elif args.db:
        DB = DBConnector(HOST, PORT, DBNAME, USER, PASS, dbtype=DBTYPE, max_disp_len=200)
"""