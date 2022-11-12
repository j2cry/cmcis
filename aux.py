from typing import List
from telegram import ReplyKeyboardMarkup


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


class ConversationState:
    MAIN_MENU = 1
    SELECT_EVENT = 2
    REGISTRATION = 3

class TGMenu:
    WELCOME = 'Привет'
    ANNOUNCE = 'Анонсы'
    PERSONAL = 'Мои сеансы'
    GOODBYE = 'До свидания'
    BACK = 'Назад'
    ACCEPT = 'Да'
    DECLINE = 'Нет'
    ADMIN_INFO = 'Служебная информация'


class TGText:
    WELCOME = 'Привет! Меня зовут Harpy. Выбери, чем я могу тебе помочь.'       # имя лучше кириллицей
    WELCOME_ADMIN = 'Привет, Гуру'
    MENU = 'Выбери, чем я могу тебе помочь.'
    END = 'До встречи!'
    EVENTS = 'Запланированные сеансы'
    MY_EVENTS = 'Мои сеансы'
    NO_EVENTS = 'Нет запланированных сеансов'
    NO_MY_EVENTS = 'Вы пока не записаны на сеансы '
    BACK = 'Назад'
    FREE_PLACES = 'осталось мест'
    ERROR = 'Кажется, что-то пошло не так. Попробуй еще раз.'
    NOT_MODIFIED = 'Изменения не внесены'
    ADMIN_REQUEST = 'Скачать информацию о записях?'
    ALREADY_REGISTRED = 'Вы уже записаны на сеанс, хотите отменить запись?'
    NOT_YET_REGISTRED = 'Вы еще не записаны, хотите записаться?'
    REGISTED_ACCEPT = 'Вы записаны на'
    REGISTER_CANCEL = 'Вы отменили запись на'
    DOWNLOAD = 'Запрошен файл по'
    ACTION_CANCELED = 'Действие отменено.'
    ADMIN = 'Служебная информация'
    YES = 'Да'
    NO = 'Нет'
    HELLO = 'Привет!'
