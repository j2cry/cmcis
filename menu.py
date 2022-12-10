from typing import List, Dict
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ParseMode
from states import ConversationState, CallbackData, ErrorState, CallbackState
from functools import wraps
from inspect import Parameter, signature
from predefined import MAXBOOK


def build_reply(schema: List[List], **kwargs):
    """ Create telegram chat menu as keyboard from list of lists with button names """
    return ReplyKeyboardMarkup(schema, **kwargs)

def build_inline(schema: List[Dict], **kwargs):
    """ Create telegram chat menu as inline keyboard from list of dictss with button names """
    return InlineKeyboardMarkup([[InlineKeyboardButton(k, callback_data=v) for k, v in row.items()] for row in schema], **kwargs)


class MenuHandler:
    """ Menu interactions handler """
    def __init__(self, text):
        self.text = text

    def answer(method):
        """ Send answer to callback """
        @wraps(method)
        def wrapper(self, update, context, **kwargs):
            if hasattr(update, 'callback_query') and (query := update.callback_query):
                query.answer()
            else:
                query = update
            return method(self, query, context, **kwargs)
        return wrapper

    def parse_parameters(method):
        """ Parse selected context parameters """
        @wraps(method)
        def wrapper(self, query, context):
            # collect required KEYWORD_ONLY parameters from context or use defaults
            required_kw = {pname: context.user_data.get(pname, pvalue.default if pvalue.default != Parameter.empty else None)
                           for pname, pvalue in signature(method).parameters.items() if pvalue.kind == Parameter.KEYWORD_ONLY}
            # TODO ? collect POSITIONAL_OR_KEYWORD parameters: cbstate, cbprev ?
            # update menu callback state
            cbstate = CallbackState(*query.data.split(':') if hasattr(query, 'data') else [])    # target callback state
            history = context.user_data.get('history', [])
            if cbstate.value == CallbackData.BACK:
                history.pop()
            elif cbstate.button == CallbackData.MAIN:
                history = [cbstate, ]
            else:
                history.append(cbstate)
            context.user_data['history'] = history

            print('menu history', *history, '-' * 25, sep='\n')
            required_kw['cbstate'] = history[-1]
            if 'cbprev' in required_kw:
                required_kw['cbprev'] = history[-2] if len(history) > 1 else CallbackState()

            result = method(self, query, context, **required_kw)
            return result
        return wrapper

    @answer
    @parse_parameters
    def main(self, query, context, cbstate=None, *, uid, connector):
        """ Show main menu """
        # parse additional required context parameters
        is_admin = connector.get_user_field(uid, field='is_admin')
        cvstate = context.user_data['cvstate']      # conversation state
        # build keyboard
        kbd = build_inline([
            {self.text['BUTTON', 'EVENTS']: CallbackData.EVENTS},
            {self.text['BUTTON', 'BOOKING']: CallbackData.BOOKING},
            {self.text['BUTTON', 'SERVICE']: CallbackData.SERVICE} if is_admin else {},
            {self.text['BUTTON', 'ABOUT']: CallbackData.ABOUT},
            {self.text['BUTTON', 'GOODBYE']: CallbackData.GOODBYE},
        ])
        self.__delete_messages(context)
        infotext = self.text['MESSAGE', 'WELCOME', 2] if (cbstate.button == CallbackData.MAIN) else self.text['MESSAGE', 'WELCOME', cvstate] % context.user_data['specname']
        context.user_data['last_messages'] = [query.message.reply_text(infotext, reply_markup=kbd)]
        return ConversationState.MENU

    @answer
    @parse_parameters
    def available_activities(self, query, context, cbstate=None, *, uid, connector):
        """ Show available activities """
        # setup context
        context.user_data['evfilter'] = cbstate.button
        # request actual events depending on pressed button
        events = connector.get_events(cbstate.button, uid=uid)
        booked = [ev for ev in events if ev['is_booked']]
        # build zero-events keyboard
        kbd = build_inline([
            {self.text['BUTTON', 'TO_RELATED_CHANNEL']: CallbackData.MAIN},     # TODO link to channel
            {self.text['BUTTON', 'TO_MAIN_MENU']: CallbackData.MAIN}
        ]) if not events else build_inline([
            {self.text['BUTTON', 'TO_EVENTS']: CallbackData.EVENTS},
            {self.text['BUTTON', 'TO_MAIN_MENU']: CallbackData.MAIN}
        ]) if not booked and (cbstate.button == CallbackData.BOOKING) else None
        # setup zero-events text
        if cbstate.button == CallbackData.EVENTS:
            TEXT = self.text['MESSAGE', 'EVENTS', bool(events)]
        elif cbstate.button == CallbackData.BOOKING:      # for BOOKING: check announces
            TEXT = self.text['MESSAGE', 'BOOKS', bool(booked) if events else 2]
            events = booked
        # push message
        evlist = [query.message.edit_text(TEXT, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)]
        # collect events list
        for num, ev in enumerate(events, 1):
            kbd = build_inline([
                {
                    self.text['BUTTON', 'MORE']: f'{CallbackData.MORE}:{ev["activity_id"]}',
                    self.text['BUTTON', 'BOOK', bool(ev['is_booked'])]: f'{CallbackData.BOOK}:{ev["activity_id"]}'
                },
                # {self.text['BUTTON', 'BACK']: f'{context.user_data["history"][-2].button}'} if num == len(events) else {},    # BACK button example
                {self.text['BUTTON', 'TO_MAIN_MENU']: CallbackData.MAIN} if num == len(events) else {},
            ])
            # TODO настроить отображение карточки анонса
            infocard = f"*{ev['activity_title']}*\n" \
                        f"{ev['showtime'].strftime('%d/%m/%Y %H:%M')}, {ev['place_title']}\n" \
                        f"{(ev['announce']) if ev['announce'] else ''}\n" \
                        f"{self.text['FILLER', 'LEFT_PLACES']}: {ev['left_places']}\n" \
                        f""
                        # TODO текст по state: про места, очередь, бронирование итп
            evlist.append(query.message.reply_text(infocard, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN))
        context.user_data['last_messages'] = evlist
        return ConversationState.MENU

    @answer
    @parse_parameters
    def service_activities(self, query, context, cbstate=None, *, uid, connector):
        """ Manage actual activities """
        # setup context
        context.user_data['evfilter'] = cbstate.button
        # request actual events depending on pressed button
        events = connector.get_events(cbstate.button, uid=uid)
        # build zero-events keyboard
        kbd = build_inline([
            {self.text['BUTTON', 'TO_MAIN_MENU']: CallbackData.MAIN}
        ]) if not events else None
        TEXT = self.text['MESSAGE', 'EVENTS', 2 + bool(events)]
        # push message
        evlist = [query.message.edit_text(TEXT, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)]
        # collect events list
        for num, ev in enumerate(events, 1):
            kbd = build_inline([
                {
                    'demo button': f'demo:{ev["activity_id"]}'
                },
                {self.text['BUTTON', 'TO_MAIN_MENU']: CallbackData.MAIN} if num == len(events) else {},
            ])
            # prepare infocard
            infocard = f"*{ev['activity_title']}*\n" \
                        f"{ev['showtime'].strftime('%d/%m/%Y %H:%M')}, {ev['place_title']}\n"
            evlist.append(query.message.reply_text(infocard, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN))
        context.user_data['last_messages'] = evlist
        return ConversationState.MENU

    @answer
    @parse_parameters
    def activity_info(self, query, context, cbstate=None, *, cbprev, uid, connector, evfilter):
        """ Show activity large infocard """
        self.__delete_messages(context)
        # request event information depending on pressed button     TODO убрать в декоратор?
        ev = connector.get_events(evfilter, uid=uid, eid=cbstate.value)
        if not ev:
            return self.raise_error(query, context, state=ErrorState.UNAVAILABLE)
        # prepare infocard
        infocard = f"*{ev['activity_title']}*\n" \
                    f"{ev['showtime'].strftime('%d/%m/%Y %H:%M')}, {ev['place_title']}\n" \
                    f"{ev['addr']}\n" \
                    f"{ev['info']}\n" \
                    f"{self.text['FILLER', 'LEFT_PLACES']}: {ev['left_places']}"
        # prepare keyboard
        kbd = build_inline([
            {self.text['BUTTON', 'BOOK', bool(ev['is_booked'])]: f'{CallbackData.BOOK}:{ev["activity_id"]}'},
            {self.text['BUTTON', 'SHOWMAP']: f'{CallbackData.SHOWMAP}:{ev["activity_id"]}'},
            {self.text['BUTTON', 'BACK']: f'{cbprev.button}:{CallbackData.BACK}'},
            {self.text['BUTTON', 'TO_MAIN_MENU']: CallbackData.MAIN}
        ])
        # push message
        context.user_data['last_messages'] = [query.message.reply_text(infocard, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)]
        return ConversationState.MENU

    @answer
    @parse_parameters
    def showmap(self, query, context, cbstate=None, *, cbprev, uid, connector, evfilter):
        """ Show address & map """
        # request event information depending on menu section   TODO убрать в декоратор?
        ev = connector.get_events(evfilter, uid=uid, eid=cbstate.value)
        if not ev:
            return self.raise_error(query, context, state=ErrorState.UNAVAILABLE)
        # prepare infocard
        infocard = f"Тут будет карта."      # TODO map link
        # prepare keyboard
        kbd = build_inline([
            {self.text['BUTTON', 'BACK']: f'{cbprev.button}:{CallbackData.BACK}'},
            {self.text['BUTTON', 'TO_MAIN_MENU']: CallbackData.MAIN}
        ])
        # push message
        context.user_data['last_messages'] = [query.message.edit_text(infocard, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)]
        return ConversationState.MENU

    @answer
    @parse_parameters
    def book(self, query, context, cbstate=None, *, cbprev, uid, connector, evfilter):
        """ Booking sheet """
        # request event information depending on menu section   TODO убрать в декоратор?
        ev = connector.get_events(evfilter, uid=uid, eid=cbstate.value)
        if not ev:
            return self.raise_error(query, context, state=ErrorState.UNAVAILABLE)
        # prepare infocard
        left_places_state = 1 + (ev['left_places'] > 1)
        infocard = self.text['MESSAGE', 'BOOK_PROCESS'] + ' ' + self.text['MESSAGE', 'BOOK_PROCESS', left_places_state]
        parameters = (
            connector.get_user_field(uid, field='specname'),
            ev['activity_title'],
            ev['showtime'].strftime('%d/%m/%Y'),
            ev['showtime'].strftime('%H:%M'),
            ev['place_title']
        )
        # prepare keyboard
        kbd = build_inline([
            {self.text['BUTTON', 'BOOK_QUANTITY']: f'{CallbackData.CONFIRM}:1'} if ev['left_places'] == 1 else
            {n if n <= MAXBOOK else f"{n} {self.text['BUTTON', 'BOOK_QUANTITY', 1]}": f'{CallbackData.CONFIRM}:{n}' for n in range(1, min(MAXBOOK + 1, ev['left_places']) + 1)},
            {self.text['BUTTON', 'BACK']: f'{cbprev.button}:{CallbackData.BACK}'},
            # {self.text['BUTTON', 'MORE']: f'{MenuCallbackData.EVCARD}:{CallbackData.MORE}:{ev["activity_id"]}'},      # NOTE backup
            # {self.text['BUTTON', 'TO_EVENTS']: f'{MenuCallbackData.EVLIST}:{CallbackData.BACK}'},                     # NOTE backup
            {self.text['BUTTON', 'TO_MAIN_MENU']: CallbackData.MAIN}
        ])
        # push message
        self.__delete_messages(context)
        context.user_data['last_messages'] = [query.message.reply_text(infocard % parameters, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)]
        return ConversationState.MENU

    @answer
    @parse_parameters
    def confirm(self, query, context, cbstate=None, *, cbprev, uid, connector, evfilter):
        """ General confirm sheet """
        print('='*25)
        print('GENERAL CONFIRM METHOD')
        print(cbprev, cbstate, sep='\n')        
        return self.raise_error(query, context, state=ErrorState.INDEV)

    # def action(self, update, context):
    #     """ Handle actions """
    #     if not (query := update.callback_query):
    #         query = update
    #     else:
    #         query.answer()
    #     # button callback data: previous and target
    #     cbprev = context.user_data.get('cbstate', CallbackState())        # previous state
    #     cbtarget = CallbackState(*query.data.split(':') if hasattr(query, 'data') else ['action', None, None])       # target state
    #     callback = getattr(self, f'_{self.__class__.__name__}__{cbtarget.button}_callback', self.raise_error)
    #     return callback(query, context)

    def __delete_messages(self, context):
        evlist = context.user_data.get('last_messages', None)
        if not evlist:
            return
        for ev in evlist:
            try:
                ev.delete()
            except:
                print(f'It seems, this message was deleted by the user: {ev["message_id"]}')
        context.user_data['last_messages'] = []

    @answer
    def raise_error(self, query, context, state=ErrorState.UNKNOWN):
        self.__delete_messages(context)
        context.user_data.clear()
        kbd = build_reply([[self.text['BUTTON', 'HELLO']]], one_time_keyboard=True, resize_keyboard=True)
        context.user_data['last_messages'] = [query.message.reply_text(self.text['MESSAGE', 'ERROR', state], reply_markup=kbd)]
        return ConversationState.END

    @answer
    def goodbye(self, update, context):
        self.__delete_messages(context)
        context.user_data.clear()
        kbd = build_reply([[self.text['BUTTON', 'HELLO']]], one_time_keyboard=True, resize_keyboard=True)
        context.user_data['last_messages'] = [update.message.reply_text(self.text['MESSAGE', 'GOODBYE', '@random'], reply_markup=kbd)]
        # context.job_queue.run_once(lambda _: message.delete(), 2)     # run delayed task
        return ConversationState.END
