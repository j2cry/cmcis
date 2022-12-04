import pathlib
import configparser
import random
from telegram.ext import ConversationHandler
from collections import namedtuple


class MenuCallbackData:
    """ Menu sheets callback data prefix """
    MAIN = 'main'
    EVLIST = 'evlist'       # for announces/booking/service menu
    EVCARD = 'evcard'       # event info card
    EVBOOK = 'evbook'       # event booking page
    EVMAP = 'evmap'         # show map and address


class ButtonCallbackData:
    """ Button callback data prefix """
    EVENTS = 'events'
    BOOKING = 'booking'
    SERVICE = 'service'
    ABOUT = 'about'
    GOODBYE = 'goodbye'
    BACK = 'back'
    TO_MAIN_MENU = 'to_main_menu'
    MORE = 'more'
    BOOK = 'book'
    SHOWMAP = 'showmap'


class ErrorState:
    UNKNOWN = 0
    TIMEOUT = 1
    INDEV = 2
    UNAVAILABLE = 3


CallbackState = namedtuple('CallbackState', 'menu,button,value', defaults=[None] * 3)


class ConversationState:
    END = ConversationHandler.END
    FIRST_MET = 1
    BODY = 2


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
