import re
from typing import List, Dict
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from conversation import ConversationState
from collections import namedtuple


def build_reply(schema: List[List], **kwargs):
    """ Create telegram chat menu as keyboard from list of lists with button names """
    return ReplyKeyboardMarkup(schema, **kwargs)

def build_inline(schema: List[Dict], **kwargs):
    """ Create telegram chat menu as inline keyboard from list of dictss with button names """
    return InlineKeyboardMarkup([[InlineKeyboardButton(k, callback_data=v) for k, v in row.items()] for row in schema], **kwargs)


class MenuCallbackData:
    """ Menu sheets callback data prefix """
    MAIN = 'main'
    INFO = 'info'       # for announces/booking/service menu


class ButtonCallbackData:
    """ Button callback data prefix """
    EVENTS = 'events'
    BOOKING = 'booking'
    SERVICE = 'service'
    ABOUT = 'about'
    GOODBYE = 'goodbye'
    BACK = 'back'
    TO_MAIN_MENU = 'to_main_menu'


class ErrorState:
    UNKNOWN = 0
    TIMEOUT = 1


CallbackState = namedtuple('CallbackState', 'cbtype,menu,button', defaults=[None, None, None])


class MenuHandler:
    """ Menu interactions handler """
    def __init__(self, text):
        self.text = text

    def show(self, update, context):
        """ Handle menu """
        if not (query := update.callback_query):
            query = update
        else:
            query.answer()

        # load required context parameters
        user = query.message.from_user
        connector = context.user_data['connector']
        state = context.user_data['state']      # conversation state
        is_admin = connector.get_user_field(user['id'], field='is_admin')
        
        # button callback data: previous and target
        cbprev = context.user_data.get('cbstate', CallbackState())        # previous state
        cbtarget = CallbackState(*query.data.split(':') if hasattr(query, 'data') else ['menu', MenuCallbackData.MAIN, None])       # target state
        context.user_data['cbstate'] = cbtarget
        # print(f'move from: {cbprev.menu}', f'move to: {cbtarget.menu}', sep='\n')

        # build required menu NOTE remove keyboard builder?
        if cbtarget.menu == MenuCallbackData.MAIN:
            # kbd = self.keyboard.from_template(cbtarget.menu, is_admin=is_admin)
            kbd = build_inline([
                {self.text['BUTTON', 'EVENTS']: f'menu:{MenuCallbackData.INFO}:{ButtonCallbackData.EVENTS}'},
                {self.text['BUTTON', 'BOOKING']: f'menu:{MenuCallbackData.INFO}:{ButtonCallbackData.BOOKING}'},
                {self.text['BUTTON', 'SERVICE']: f'menu:{MenuCallbackData.INFO}:{ButtonCallbackData.SERVICE}'} if is_admin else {},
                {self.text['BUTTON', 'ABOUT']: f'action::{ButtonCallbackData.ABOUT}'},
                {self.text['BUTTON', 'GOODBYE']: f'action::{ButtonCallbackData.GOODBYE}'},
            ])

            # TODO если приход из BACK, то другой conversation state: Вы находитесь в главном меню...
            if (cbtarget.button == ButtonCallbackData.TO_MAIN_MENU):
                query.message.edit_text(self.text['MESSAGE', 'WELCOME', 2], reply_markup=kbd)
            else:
                context.user_data['last_message'] = query.message.reply_text(self.text['MESSAGE', 'WELCOME', state] % context.user_data['specname'], reply_markup=kbd)
            # push_message = query.message.edit_text if (cbtarget.button == ButtonCallbackData.TO_MAIN_MENU) else query.message.reply_text
            # context.user_data['last_message'] = push_message(self.text['MESSAGE', 'WELCOME', state] % context.user_data['specname'], reply_markup=kbd)
        
        elif cbtarget.menu == MenuCallbackData.INFO:
            # TODO DB request depending on pressed button
            events = connector.get_events(cbtarget.button, uid=user['id'])

            print(f'button: {cbtarget.button}', *events, sep='\n')        # DEBUG FEATURE

            kbd = build_inline([
                # ...
                # {self.text['BUTTON', 'BACK']: f'menu:{MenuCallbackData.MAIN}:'},  # TODO collect 
                {self.text['BUTTON', 'TO_MAIN_MENU']: f'menu:{MenuCallbackData.MAIN}:{ButtonCallbackData.TO_MAIN_MENU}'},
            ])
            query.message.edit_text('next step menu', reply_markup=kbd)
        
        else:       # broken menu state
            self.__error_callback(query, context)

    
        # context.user_data['cbstate'] = cbtarget     # refresh cbstate if there was no exception
        return ConversationState.BODY

    def action(self, update, context):
        """ Handle actions """
        if not (query := update.callback_query):
            query = update
        else:
            query.answer()
        # load required context parameters
        # user = query.message.from_user
        # connector = context.user_data['connector']
        # state = context.user_data['state']      # conversation state
        # is_admin = connector.get_user_field(user['id'], field='is_admin')

        # button callback data: previous and target
        cbprev = context.user_data.get('cbstate', CallbackState())        # previous state
        cbtarget = CallbackState(*query.data.split(':') if hasattr(query, 'data') else ['action', None, None])       # target state

        callback = getattr(self, f'_{self.__class__.__name__}__{cbtarget.button}_callback', self.raise_error)
        return callback(query, context)

    def raise_error(self, update, context, state=ErrorState.UNKNOWN):
        if not (query := update.callback_query):
            query = update
            context.user_data['last_message'].delete()
        else:
            query.message.delete()
            query.answer()
        context.user_data.clear()
        kbd = build_reply([[self.text['BUTTON', 'HELLO']]], one_time_keyboard=True, resize_keyboard=True)
        query.message.reply_text(self.text['MESSAGE', 'ERROR', state], reply_markup=kbd)
        return ConversationState.END

    def __goodbye_callback(self, update, context):
        update.message.delete()
        context.user_data.clear()
        kbd = build_reply([[self.text['BUTTON', 'HELLO']]], one_time_keyboard=True, resize_keyboard=True)
        update.message.reply_text(self.text['MESSAGE', 'GOODBYE', '@random'], reply_markup=kbd)
        return ConversationState.END
        