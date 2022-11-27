import re
import keyring
import psycopg2
from psycopg2.extras import DictCursor
from functools import wraps
from menu import ButtonCallbackData
from string import punctuation
from datetime import datetime


SERVICE_INTERVAL = '7 day'


class ShowEvent(dict):
    """ Event object """
    @property
    def free_places(self):
        if self['visitors']:
            return self['max_visitors'] - len(self['visitors'])
        else:
            return self['max_visitors']

    def isregistred(self, uid):
        val = uid in self['visitors'] if self['visitors'] else False
        return val
    
    def formatted_title(self, multirow=False):
        return self['showtime'].strftime('%d/%m/%Y, %H:%M') + ('\n' if multirow else ' ') + self['title']

    @property
    def filename(self):
        return re.sub(rf'[{punctuation}]|\s', '_', self.formatted_title()) + '.csv'
    
    @property
    def past(self):
        return self['showtime'] < datetime.now()


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
        POSSIBLE_FIELDS = ('specname', 'username', 'first_name', 'last_name', 'is_admin')
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
        self.__cursor.execute(BASIC_QUERY, (client_id, *[v for k, v in kwargs.items() if k in fields]))
    
    @manage_connection
    def get_user_field(self, client_id, *, field, default=None):
        """ Get user info field or default if not exists """
        self.__cursor.execute(f'SELECT {field} FROM {self.schema}.client WHERE client_id = %s', (client_id, ))
        user_info = self.__cursor.fetchall()
        return user_info[0].get(field, default) if user_info else {}

    @manage_connection
    def get_events(self, mode, **kwargs):
        """ Get required events """
        # TODO объединить EVENTS и BOOKING - для них набор ивентов будет одинаковый - отличия в менюшках
        if mode == ButtonCallbackData.EVENTS:
            condition = '''a.active AND (a.openreg <= NOW()) AND (NOW() < a.showtime)
                AND (r.visitors is NULL OR 
                    ((CARDINALITY(r.visitors) < a.max_visitors) AND (%s != ALL(r.visitors))))'''
            parameters = (kwargs.get('uid'), )
        elif mode == ButtonCallbackData.BOOKING:
            condition = 'a.active AND (NOW() < a.showtime) AND %s = ANY(r.visitors)'
            parameters = (kwargs.get('uid'), )
        elif mode == ButtonCallbackData.SERVICE:
            condition = 'a.active AND (NOW() < a.showtime + INTERVAL %s)'
            parameters = (SERVICE_INTERVAL, )
        else:
            return []

        QUERY = f'''
            WITH reg AS
                (SELECT activity_id, ARRAY_AGG(client_id) visitors 
                FROM {self.schema}.booking 
                WHERE actual
                GROUP BY activity_id) 
            SELECT a.activity_id, a.title, a.place, a.max_visitors, a.showtime, a.info, r.visitors 
            FROM {self.schema}.activity a 
            LEFT JOIN reg r ON r.activity_id = a.activity_id 
            WHERE {condition}
            ORDER BY a.showtime
            '''

        self.__cursor.execute(QUERY, parameters)
        result = [ShowEvent(ev) for ev in self.__cursor.fetchall()]
        return result

    @manage_connection
    def set_registration(self, client_id, activity_id, value):
        """ Update user registration row """
        BASIC_QUERY = f'''
            INSERT INTO {self.schema}.booking (client_id, activity_id, actual, modified, num_changes) 
            VALUES (%s, %s, %s, NOW(), 0) 
            ON CONFLICT (client_id, activity_id) DO UPDATE 
            SET actual = EXCLUDED.actual,
                modified = EXCLUDED.modified,
                num_changes = {self.schema}.booking.num_changes + 1'''
        parameters = (client_id, activity_id, value)
        self.__cursor.execute(BASIC_QUERY, parameters)
    
    @manage_connection
    def get_visitors_info(self, activity_id):
        BASIC_QUERY = f'''
            SELECT c.*, b.num_changes FROM {self.schema}.client c
            JOIN {self.schema}.booking b on b.client_id = c.client_id
            WHERE (b.activity_id = %s) AND b.actual'''
        self.__cursor.execute(BASIC_QUERY, (activity_id, ))
        return [dict(item) for item in self.__cursor.fetchall()]
