from time import sleep

from neo4j import GraphDatabase, Session

from backend.config import config


class Database:
    DB_URI = f'neo4j://{config.db_hostname}:{config.db_port}'

    def __init__(self) -> None:
        print(f'Waiting for the database to be up before connecting...')
        sleep(60)
        print(f'Attempting to connect to the database at {self.DB_URI}')
        self._driver = GraphDatabase.driver(self.DB_URI, auth=(config.db_username, config.db_password))
        with self.session as init_session:
            init_session.run('CREATE CONSTRAINT unique_username IF NOT EXISTS '
                             'ON (n:User) '
                             'ASSERT n.username IS UNIQUE')
            init_session.run('CREATE CONSTRAINT unique_post_uuid IF NOT EXISTS '
                             'ON (p:Post) '
                             'ASSERT p.uuid IS UNIQUE')

    @property
    def session(self) -> Session:
        print('Staring DB session')
        return self._driver.session()

    def __del__(self) -> None:
        if hasattr(self, '_driver'):
            self._driver.close()
            print('Ending DB connection')


database = Database()
del Database
