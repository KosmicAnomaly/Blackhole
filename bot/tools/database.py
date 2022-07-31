from os import getenv
import logging
import sys

import psycopg

logger = logging.getLogger("kosmo")


class Database():
    def __init__(self):

        self.initialized = False

        try:
            self.conn = psycopg2.connect(
                host=getenv("POSTGRES_DB_HOST"),
                port=getenv("POSTGRES_DB_PORT"),
                database=getenv("POSTGRES_DB_NAME"),
                user=getenv("POSTGRES_DB_USERNAME"),
                password=getenv("POSTGRES_DB_PASSWORD")
            )

            statement = """
            SELECT version();
            """

            db_version = self.execute(statement, count=1)

            logger.info(
                f"Connected to the PostgreSQL database\nversion {' - '.join(db_version)}")

            self.initialized = True

        except (Exception, psycopg2.DatabaseError) as error:
            logger.critical(
                f"Failed to connect to PostgreSQL database:\n{error}")
            sys.exit("Failed to connect to PostgreSQL database")

    def execute(self, statement: str, parameters: tuple = None, count: int = None):
        cur = self.conn.cursor()
        try:
            cur.execute(statement, parameters)
            self.conn.commit()
        except:
            cur.close()
            self.conn.rollback()
            logger.error(
                f'Failed to execute statement "{statement}" using parameters "{parameters}"', exc_info=True)
            raise
        else:
            if count and cur.rowcount >= 1:
                if count == 1:
                    results = cur.fetchone()
                elif count == -1:
                    results = cur.fetchall()
                else:
                    results = cur.fetchmany(count)
            else:
                results = None
            cur.close()
            return results
