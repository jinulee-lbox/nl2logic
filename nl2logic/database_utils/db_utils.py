from typing import *
import logging

import pymysql
import pymysql.cursors
from ..config import nl2logic_config as config

dbconfig = config.database

class DatabaseAPI():

    def __init__(self, db: str):
        self.database = db
        try:
            conn = pymysql.connect(
                user=dbconfig.user,
                password=dbconfig.password,
                host=dbconfig.host,
                port=dbconfig.port,
                database=self.database,
                cursorclass=pymysql.cursors.DictCursor
            )
            self.conn = conn
        except pymysql.Error as e:
            # closed database
            logging.error(e)

    def query(self, sql: str, params: Union[tuple, None] = None):
        sql = sql.strip()
        logging.debug(sql)

        with self.conn.cursor() as cursor:
            try:
                cursor.execute(f"USE {self.database}")
                cursor.execute(sql, params)
                self.conn.commit()
                return cursor.fetchall()
            except Exception as e:
                raise e

    def close(self):
        self.conn.close()