import re
from typing import List
from telegram import ReplyKeyboardMarkup
from string import punctuation


def build_menu(schema: List[List], **kwargs):
    """ Create telegram chat menu from list of lists with button names """
    return ReplyKeyboardMarkup(schema, **kwargs)


def save_report(filename, raw, sep=';', encoding='utf-8'):
    """ Save visitors information """
    head = sep.join(raw[0].keys()) + '\n'
    data = [sep.join([str(v) if v else '' for v in r.values()]) + '\n' for r in raw]
    with open(filename, 'w', encoding=encoding) as f:
        f.writelines([head, *data])


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
        print(val)
        return val
    
    def formatted_title(self, multirow=False):
        return self['showtime'].strftime('%d/%m/%Y, %H:%M') + ('\n' if multirow else ' ') + self['title']

    @property
    def filename(self):
        return re.sub(rf'[{punctuation}]|\s', '_', self.formatted_title()) + '.csv'


class ConversationState:
    MAIN_MENU = 1
    SELECT_EVENT = 2
    REGISTRATION = 3

class TGMenu:
    WELCOME = 'Привет'
    ANNOUNCE = 'Доступные сеансы'
    PERSONAL = 'Мои записи'
    GOODBYE = 'До свидания'
    BACK = 'Назад'
    ACCEPT = 'Да'
    DECLINE = 'Нет'
    ADMIN_INFO = 'Служебная информация'


class TGText:
    WELCOME = 'Привет! Меня зовут Harpy. Выберите, чем я могу вам помочь.'
    WELCOME_ADMIN = 'Привет, Гуру'
    MENU = 'Выберите, чем я могу вам помочь.'
    END = 'До встречи!'
    EVENTS = 'Вот доступные сеансы, на которые вы еще не зарегистрированы. Сеансы, на которые вы уже зарегистрированы, можно найти в разделе "Мои записи"'
    MY_EVENTS = 'Вот сеансы, на которые вы записаны'
    NO_EVENTS = 'Нет анонсированных сеансов'
    NO_MY_EVENTS = 'У вас еще нет записей на сеансы'
    BACK = 'Назад'
    FREE_PLACES = 'На этот сеанс осталось %s мест'
    ERROR = 'Кажется, что-то пошло не так. Попробуйте еще раз.'
    ADMIN_REQUEST = 'Скачать информацию о записях?'
    ALREADY_REGISTRED = 'Вы уже записаны на сеанс, хотите отменить запись?'
    NOT_YET_REGISTRED = 'Вы еще не записаны, хотите записаться?'
    REGISTED_ACCEPT = 'Вы записаны на сеанс'
    REGISTER_CANCEL = 'Вы отменили запись на сеанс'
    DOWNLOAD = 'Запрошен файл по'
    ACTION_CANCELED = 'Изменения не внесены'
    ADMIN_EVENTS = 'Служебная информация: сеансы'
    YES = 'Да'
    NO = 'Нет'
    HELLO = 'Привет!'
    NO_REGISTRATIONS = 'На этот сеанс еще никто не зарегистрирован.'
