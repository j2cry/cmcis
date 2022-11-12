import keyring
import psycopg2
from psycopg2.extras import DictCursor
from functools import wraps
from aux import TGMenu, ShowEvent


OPEN_REG_INTERVAL = '1 month'        # TODO in SQL column


class BotConnector():
    """ PostgreSQL bot connector """
    def __init__(self, dbname, username, *, schema='public', host='localhost', port=5432):
        self.dbname = dbname
        self.username = username
        self.schema = schema
        self.host = host
        self.port = port
        self.__conn = None
        self.__cursor = None
    
    def manage_connection(method):
        """ Connection manager for methods """
        @wraps(method)
        def wrapper(self, *args, **kwargs):
            self.__conn = psycopg2.connect(dbname=self.dbname, user=self.username, 
                                           password=keyring.get_password(self.dbname, self.username), 
                                           host=self.host, port=self.port)
            self.__conn.autocommit = True
            self.__cursor = self.__conn.cursor(cursor_factory=DictCursor)
            result = method(self, *args, **kwargs)      # run method
            self.__cursor.close()
            self.__conn.close()            
            return result
        return wrapper
    
    @manage_connection
    def set_user(self, client_id, **kwargs):
        """ Add or update user, return admin status """
        POSSIBLE_FIELDS = ('username', 'first_name', 'last_name', 'is_admin')
        fields = [f for f in kwargs.keys() if f in POSSIBLE_FIELDS]
        fieldholder = (', ' + ', '.join(fields)) if len(fields) else ''
        paramholder = (', ' + ', '.join(['%s'] * len(fields))) if len(fields) else ''
        # collect on conflict condition
        set_condition = ', '.join([f'{f} = EXCLUDED.{f}' for f in fields])
        on_conflict = f'UPDATE SET {set_condition}' if len(fields) else 'NOTHING'

        BASIC_QUERY = f'''
            INSERT INTO {self.schema}.client (client_id{fieldholder})
            VALUES (%s{paramholder})
            ON CONFLICT (client_id) DO {on_conflict}'''
        self.__cursor.execute(BASIC_QUERY, (client_id, *kwargs.values()))
    
    @manage_connection
    def get_user_admin(self, client_id):
        """ Get user info """
        self.__cursor.execute(f'SELECT is_admin FROM {self.schema}.client WHERE client_id = %s', (client_id, ))
        user_info = self.__cursor.fetchall()
        return user_info[0]['is_admin'] if user_info else False

    @manage_connection
    def get_events(self, mode, **kwargs):
        """ Get required events """
        BASIC_QUERY = f'''
            WITH reg AS
                (SELECT activity_id, ARRAY_AGG(client_id) visitors 
                FROM {self.schema}.booking 
                WHERE actual
                GROUP BY activity_id) 
            SELECT a.activity_id, title, place, max_visitors, showtime, description, r.visitors 
            FROM {self.schema}.activity a 
            LEFT JOIN reg r ON r.activity_id = a.activity_id 
            WHERE (NOW() < showtime)'''
        
        if mode == TGMenu.ANNOUNCE:
            add_condition = ''' 
                AND (showtime < (NOW() + INTERVAL %s)) 
                AND (r.visitors is NULL OR 
                    ((CARDINALITY(r.visitors) < a.max_visitors) AND (%s != ALL(r.visitors))))'''
            parameters = (OPEN_REG_INTERVAL, kwargs.get('uid'))
        elif mode == TGMenu.PERSONAL:
            add_condition = ' AND %s = ANY(r.visitors)'
            parameters = (kwargs.get('uid'), )
        elif mode == TGMenu.ADMIN_INFO:
            add_condition = ''
            parameters = None

        self.__cursor.execute(BASIC_QUERY + add_condition, parameters)
        result = [ShowEvent(ev) for ev in self.__cursor.fetchall()]
        return result

    @manage_connection
    def set_registration(self, client_id, activity_id, value):
        """ Update user registration row """
        BASIC_QUERY = f'''
            INSERT INTO {self.schema}.booking (client_id, activity_id, actual, modified, changes) 
            VALUES (%s, %s, %s, NOW(), 0) 
            ON CONFLICT (client_id, activity_id) DO UPDATE 
            SET actual = EXCLUDED.actual,
                modified = EXCLUDED.modified,
                changes = {self.schema}.booking.changes + 1'''
        parameters = (client_id, activity_id, value)
        self.__cursor.execute(BASIC_QUERY, parameters)
    
    @manage_connection
    def get_visitors_info(self, activity_id):
        BASIC_QUERY = f'''
            SELECT c.*, b.changes FROM {self.schema}.client c
            JOIN {self.schema}.booking b on b.client_id = c.client_id
            WHERE (b.activity_id = %s) AND b.actual'''
        self.__cursor.execute(BASIC_QUERY, (activity_id, ))
        return [dict(item) for item in self.__cursor.fetchall()]
