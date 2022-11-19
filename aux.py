import os
import re
import pathlib
from typing import List
from telegram import ReplyKeyboardMarkup, ParseMode
from string import punctuation
from dictionary import TGMenu, TGText
from functools import wraps
from datetime import datetime


def build_keyboard(schema: List[List], **kwargs):
    """ Create telegram chat menu as keyboard from list of lists with button names """
    return ReplyKeyboardMarkup(schema, **kwargs)


def manage_menu(level):
    """ Decorator for managing menu tree """
    def __menu_manager(func):
        @wraps(func)
        def __wrapper(query, context, **kwargs):
            menu = context.user_data.get('menu_tree', [])
            if not level:
                menu.clear()
            elif len(menu) < level:
                menu.append(query.message.text)
            else:
                menu = menu[:level]
            return func(query, context, **kwargs)
        return __wrapper
    return __menu_manager


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
        return val
    
    def formatted_title(self, multirow=False):
        return self['showtime'].strftime('%d/%m/%Y, %H:%M') + ('\n' if multirow else ' ') + self['title']

    @property
    def filename(self):
        return re.sub(rf'[{punctuation}]|\s', '_', self.formatted_title()) + '.csv'
    
    @property
    def past(self):
        return self['showtime'] < datetime.now()


class ConversationState:
    MAIN_MENU = 1
    SELECT_EVENT = 2
    SELECT_EVENT_SERVICE = 3
    SELECT_ACTION = 4
    CONFIRM_ACTION = 5


class AcceptedQAPair:
    def __init__(self, question, answer):
        """ Question pair for `accepted` case """
        self.question = question if question else TGText.DEFAULT_CONFIRM_QUESTION
        self.answer = answer if answer else TGText.DEFAULT_ACCEPTED

# AcceptedQAPair = namedtuple('AcceptedQAPair', 'question,answer', defaults=(TGText.DEFAULT_CONFIRM_QUESTION, TGText.DEFAULT_ACCEPTED))


class CallbackAction:
    """ Callback with description """
    def __init__(self, callback, qpos, apos, qneg, aneg):
        """ Init action callback handler """
        self.callback = callback if callback else lambda *args, **kw: None
        self.positive = AcceptedQAPair(qpos, apos)
        self.negative = AcceptedQAPair(qneg, aneg)
        # self.positive = AcceptedQAPair(qpos if qpos else TGText.DEFAULT_CONFIRM_QUESTION, apos if apos else TGText.DEFAULT_ACCEPTED)
        # self.negative = AcceptedQAPair(qneg if qneg else TGText.DEFAULT_CONFIRM_QUESTION, aneg if aneg else TGText.DEFAULT_ACCEPTED)
    
    def __call__(self, *args, **kwargs):
        return self.callback(*args, **kwargs)


class TGActions:
    def __init__(self):
        # map button title with its variable name
        self.__mapper = {v: k.lower() for k, v in TGMenu.__dict__.items() if not (k.startswith('__') and k.endswith('__'))}
        # TODO нормальный регистратор функций

        # question/answer definitions
        self.qneg_download_registred = TGText.REGISTRATIONS_REQUEST
        self.aneg_download_registred = TGText.REGISTRATIONS_DOWNLOAD

        self.qpos_switch_register = TGText.REGISTRED_POSITIVE
        self.apos_switch_register = TGText.REGISTER_ACCEPTED        
        self.qneg_switch_register = TGText.REGISTRED_NEGATIVE
        self.aneg_switch_register = TGText.REGISTER_CANCELLED

        self.qneg_send_notify = TGText.NOTIFY_REQUEST
        self.aneg_send_notify = TGText.NOTIFY_SENT

    def get(self, name):
        fname = self.__mapper.get(name, '')
        func = getattr(self, f'func_{fname}', None)
        qpos = getattr(self, f'qpos_{fname}', None)
        apos = getattr(self, f'apos_{fname}', None)
        qneg = getattr(self, f'qneg_{fname}', None)
        aneg = getattr(self, f'aneg_{fname}', None)
        return CallbackAction(func, qpos, apos, qneg, aneg)
    
    # === action definitions ===
    # return succeed, answer_state (shows which answer to use)
    @staticmethod
    def func_download_registred(query, context):
        """ Download file with registred users """
        event = context.user_data['selected_event']
        filename = pathlib.Path('reports').joinpath(event.filename).as_posix()
        save_report(filename, context.user_data.get('report'))
        # send to chat
        with open(filename, 'rb') as file:
            query.message.reply_document(file)
        # remove file from disk
        os.remove(filename)
        return True, False

    @staticmethod
    def func_switch_register(query, context):
        """ Switch user registration """
        user = query.message.from_user
        if not (event := context.user_data.get('selected_event')):
            return False
        updated = not event.isregistred(user['id'])
        context.user_data['connector'].set_registration(user['id'], event['activity_id'], updated)
        return True, updated
    
    @staticmethod
    def func_send_notify(query, context):
        """ Notify subscribers """
        event = context.user_data['selected_event']
        params = (event['showtime'].strftime('%d/%m/%Y'), event['showtime'].strftime('%H:%M'))
        for row in context.user_data.get('report'):
            context.bot.send_message(row['client_id'], TGText.NOTIFICATION % params, parse_mode=ParseMode.MARKDOWN)
        return True, False

actions = TGActions()
