import pathlib
import configparser
import random
from telegram.ext import ConversationHandler
from collections import namedtuple


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
    USER_LINK = ['tg://user?id=%s', 'https://t.me/%s']

class ErrorState:
    UNKNOWN = 0
    TIMEOUT = 1
    INDEV = 2
    UNAVAILABLE = 3
    BOOK_DECLINED = 4


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
        return values[state]
