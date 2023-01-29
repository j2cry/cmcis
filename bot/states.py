import re
import pymorphy2
import pathlib
import configparser
import random
from telegram.ext import ConversationHandler
from collections import namedtuple
from functools import partial


class CallbackData:
    """ Button callback data """
    ERROR = 'error'
    BACK = 'back'
    MAIN = 'main'
    ANNOUNCE = 'announce'
    MYBOOKING = 'mybooking'
    SERVICE = 'service'
    ABOUT = 'about'
    GOODBYE = 'goodbye'
    MORE = 'more'
    BOOK = 'book'
    SHOWMAP = 'showmap'
    SHOWTICKET = 'showticket'
    BOOK_CONFIRM = 'confirm_book'
    BOOK_ACCEPT = 'accept_book'
    BOOK_CONFIRM_ADMIN = 'admin_confirm_book'
    USER_CONFIRN_NOTIFICATION = 'user_confirm_notification'
    USER_LINK = ['tg://user?id=%s', 'https://t.me/%s']

class ErrorState:
    UNKNOWN = 0
    TIMEOUT = 1
    INDEV = 2
    UNAVAILABLE = 3
    FORBIDDEN = 4
    SERVERSIDE = 5


CallbackState = namedtuple('CallbackState', 'button,value', defaults=[None] * 2)   # pressed button and its additional value


class HistoryState(list):
    def __getitem__(self, index=None):
        if index == None:
            index = -1
        return super().__getitem__(index)

    @property
    def prev(self):
        return self[-2] if len(self) > 2 else CallbackState()

    @property
    def current(self):
        return self[-1] if len(self) else CallbackState()


class ConversationState:
    END = ConversationHandler.END
    FIRST_MET = 1
    MENU = 2


class MorphString(str):
    def __init__(self, value):
        super().__init__()
        self.morph = pymorphy2.MorphAnalyzer()

    def agree_with_number(self, *values):
        text = self % values
        # apply morph analyzer
        variates = re.findall(r'{{(.*?)}}', text)
        varforms = [num + ' ' + self.morph.parse(word)[0].make_agree_with_number(int(num)).word for num, word in map(str.split, variates)]
        return re.sub(r'{{(.*?)}}', '{}', text).format(*varforms)


class DialogMessages:
    """ Bot answers loader """
    def __init__(self, path, sep='||'):
        filepath = pathlib.Path(path).absolute().as_posix()
        dialog = configparser.ConfigParser()
        dialog.read(filepath)
        # build messages dict
        self.__messages = {section: {k: [item.strip() for item in v.split(sep)] for k, v in dialog[section].items()} for section in dialog}

    def __getitem__(self, index):
        section, key = index[:2]
        values = self.__messages.get(section.upper(), {}).get(key.lower(), [None])

        state = index[2] if len(index) > 2 else 0
        if state == '@random':
            state = random.randint(0, len(values) - 1)
        return MorphString(values[state])
