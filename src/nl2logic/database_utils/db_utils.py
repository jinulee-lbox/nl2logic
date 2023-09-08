from typing import *

import pymysql
import pymysql.cursors


class DatabaseAPI():

    def __init__(self, db: str):
        self.database = db
        try:
            conn = pymysql.connect(
                user="annottool",
                password="annottool123",
                host="127.0.0.1",
                port=3306,
                database=self.database,
                cursorclass=pymysql.cursors.DictCursor
            ) # TODO config file
            self.conn = conn
        except pymysql.Error as e:
            # closed database
            print(e)

    def query(self, sql: str, params: Union[tuple, None] = None):
        sql = sql.strip()
        # print(sql)

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