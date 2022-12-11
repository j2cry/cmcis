from typing import List, Dict
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ParseMode
from states import ConversationState, CallbackData, ErrorState, CallbackState
from functools import wraps
from inspect import Parameter, signature
from predefined import MAXBOOK, BOT_ADMIN_USERNAME, RELATED_CHANNEL


def build_reply(schema: List[List], **kwargs):
    """ Create telegram chat menu as keyboard from list of lists with button names """
    return ReplyKeyboardMarkup(schema, **kwargs)

def build_inline(schema: List[Dict], **kwargs):
    """ Create telegram chat menu as inline keyboard from list of dictss with button names """
    return InlineKeyboardMarkup([[InlineKeyboardButton(k, **v) if isinstance(v, dict) else InlineKeyboardButton(k, callback_data=v)
                                for k, v in row.items()] for row in schema], **kwargs)


def collect_card(*parts, first_bold=True):
    prepared = [p[1] % p[0] if isinstance(p, (tuple, list)) else p for p in parts if p]
    if prepared and first_bold:
        prepared[0] = f'*{prepared[0]}*'
    return '\n'.join(prepared)


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
            {self.text['BUTTON', 'ANNOUNCE']: CallbackData.ANNOUNCE},
            {self.text['BUTTON', 'BOOKING']: CallbackData.MYBOOKING},
            {self.text['BUTTON', 'SERVICE']: CallbackData.SERVICE} if is_admin else {},
            {self.text['BUTTON', 'ABOUT']: CallbackData.ABOUT},
            {self.text['BUTTON', 'GOODBYE']: CallbackData.GOODBYE},
            {'debug action': 'DEBUG'},
        ])
        self.__delete_messages(context)
        infotext = self.text['MESSAGE', 'WELCOME', 2] if (cbstate.button == CallbackData.MAIN) else self.text['MESSAGE', 'WELCOME', cvstate] % context.user_data['specname']
        context.user_data['last_messages'] = [query.message.reply_text(infotext, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)]
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
            {self.text['BUTTON', 'TO_RELATED_CHANNEL']: {'url': RELATED_CHANNEL}},      # NOTE is it possible to handle this button?
            {self.text['BUTTON', 'TO_MAIN_MENU']: CallbackData.MAIN}
        ]) if not events else build_inline([
            {self.text['BUTTON', 'TO_ANNOUNCE']: CallbackData.ANNOUNCE},
            {self.text['BUTTON', 'TO_MAIN_MENU']: CallbackData.MAIN}
        ]) if not booked and (cbstate.button == CallbackData.MYBOOKING) else None
        # setup zero-events text
        if cbstate.button == CallbackData.ANNOUNCE:
            TEXT = self.text['MESSAGE', 'ANNOUNCE', bool(events)]
        elif cbstate.button == CallbackData.MYBOOKING:      # for BOOKING: check announces
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
            TEXT = f"*{ev['activity_title']}*\n" \
                   f"{ev['showtime'].strftime('%d/%m/%Y %H:%M')}, {ev['place_title']}\n" \
                   f"{(ev['announce']) if ev['announce'] else ''}\n" \
                   f"{self.text['FILLER', 'LEFT_PLACES']}: {ev['left_places']}\n" \
                   f""
                   # TODO текст по state: про места, очередь, бронирование итп            
            evlist.append(query.message.reply_text(TEXT, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN))
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
        TEXT = self.text['MESSAGE', 'ANNOUNCE', 2 + bool(events)]
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
            TEXT = f"*{ev['activity_title']}*\n" \
                   f"{ev['showtime'].strftime('%d/%m/%Y %H:%M')}, {ev['place_title']}\n"
            evlist.append(query.message.reply_text(TEXT, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN))
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
            return self.direct_switch(query, context, target=CallbackData.ERROR, errstate=ErrorState.UNAVAILABLE)
        # prepare infocard
        TEXT = f"*{ev['activity_title']}*\n" \
               f"{ev['showtime'].strftime('%d/%m/%Y %H:%M')}, {ev['place_title']}\n" \
               f"{ev['addr']}\n" \
               f"{ev['activity_info']}\n" \
               f"{self.text['FILLER', 'LEFT_PLACES']}: {ev['left_places']}"
        # prepare keyboard
        kbd = build_inline([
            {self.text['BUTTON', 'BOOK', bool(ev['is_booked'])]: f'{CallbackData.BOOK}:{ev["activity_id"]}'},
            {self.text['BUTTON', 'SHOWMAP']: f'{CallbackData.SHOWMAP}:{ev["activity_id"]}'},
            {self.text['BUTTON', 'SHOWTICKET']: f'{CallbackData.SHOWTICKET}:{ev["activity_id"]}'} if ev['quantity'] else {},       # TODO
            {self.text['BUTTON', 'BACK']: f'{cbprev.button}:{CallbackData.BACK}'},
            {self.text['BUTTON', 'TO_MAIN_MENU']: CallbackData.MAIN}
            # TODO добавить кнопки ПОКАЗАТЬ БИЛЕТ
        ])
        # push message
        context.user_data['last_messages'] = [query.message.reply_text(TEXT, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)]
        return ConversationState.MENU

    @answer
    @parse_parameters
    def showmap(self, query, context, cbstate=None, *, cbprev, uid, connector, evfilter):
        """ Show address & map """
        # request event information depending on menu section   TODO убрать в декоратор?
        ev = connector.get_events(evfilter, uid=uid, eid=cbstate.value)
        if not ev:
            return self.direct_switch(query, context, target=CallbackData.ERROR, errstate=ErrorState.UNAVAILABLE)
        TEXT = collect_card(ev['place_title'],
                            ev['place_info'],
                            ev['addr'],
                            (ev['maplink'], self.text["FILLER", "SHOWMAP"]),
                            )
        # prepare keyboard
        kbd = build_inline([
            {self.text['BUTTON', 'BACK']: f'{cbprev.button}:{CallbackData.BACK}'},
            {self.text['BUTTON', 'TO_MAIN_MENU']: CallbackData.MAIN}
        ])
        # push message
        context.user_data['last_messages'] = [query.message.edit_text(TEXT, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)]   # disable_web_page_preview
        return ConversationState.MENU

    @answer
    @parse_parameters
    def showticket(self, query, context, cbstate=None, *, cbprev, uid, connector, evfilter):
        """ Show ticket info """
        return self.direct_switch(query, context, target=CallbackData.ERROR, errstate=ErrorState.INDEV)

    @answer
    @parse_parameters
    def book(self, query, context, cbstate=None, *, cbprev, uid, connector, evfilter):
        """ Booking sheet """
        # request event information depending on menu section   TODO убрать в декоратор?
        ev = connector.get_events(evfilter, uid=uid, eid=cbstate.value)
        if not ev:
            return self.direct_switch(query, context, target=CallbackData.ERROR, errstate=ErrorState.UNAVAILABLE)
        # prepare infocard
        parameters = (
            connector.get_user_field(uid, field='specname'),
            ev['activity_title'],
            ev['showtime'].strftime('%d/%m/%Y'),
            ev['showtime'].strftime('%H:%M'),
            ev['place_title'],
        )
        TEXT = self.text['MESSAGE', 'BOOK_PROCESS_HEAD', ev['quantity'] > 0] % parameters + \
               f" {self.text['MESSAGE', 'BOOK_PROCESS_BODY', ev['left_places'] > 1] % ev['left_places']}" + \
               (f"\n{self.text['MESSAGE', 'BOOK_PROCESS_BODY', 2 + (ev['quantity'] > 1)] % ev['quantity']}" if ev['quantity'] else "") + \
               f" {self.text['MESSAGE', 'BOOK_PROCESS_FINAL', ev['quantity'] > 0]}"

        print('BOOKED QUANTITY:', ev['quantity'])
        print('LEFT PLACES:', ev['left_places'])

        # prepare keyboard
        available_range = range(1, min(MAXBOOK + 1, max(ev['left_places'], ev['quantity'])) + 1)
        kbd = build_inline([
            {self.text['BUTTON', 'BOOK_QUANTITY']: f'{CallbackData.BOOK_CONFIRM}:1'} if ev['left_places'] == 1 else
            {n if n <= MAXBOOK else f"{n} {self.text['BUTTON', 'BOOK_QUANTITY', 1]}": f'{CallbackData.BOOK_CONFIRM}:{n}' for n in available_range},
            {self.text['BUTTON', 'BOOK_QUANTITY', 2]: f'{CallbackData.BOOK_CONFIRM}:0'} if ev['quantity'] else {},
            {self.text['BUTTON', 'BACK']: f'{cbprev.button}:{CallbackData.BACK}'},
            # {self.text['BUTTON', 'MORE']: f'{MenuCallbackData.EVCARD}:{CallbackData.MORE}:{ev["activity_id"]}'},      # NOTE backup
            # {self.text['BUTTON', 'TO_ANNOUNCE']: f'{MenuCallbackData.EVLIST}:{CallbackData.BACK}'},                     # NOTE backup
            {self.text['BUTTON', 'TO_MAIN_MENU']: CallbackData.MAIN}
        ])
        # push message
        self.__delete_messages(context)
        context.user_data['last_messages'] = [query.message.reply_text(TEXT, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)]
        return ConversationState.MENU

    @answer
    @parse_parameters
    def book_confirm(self, query, context, cbstate=None, *, cbprev, uid, connector, evfilter):
        """ Confirm booking """
        # request event information depending on menu section
        ev = connector.get_events(evfilter, uid=uid, eid=cbprev.value)
        if not ev:
            return self.direct_switch(query, context, target=CallbackData.ERROR, errstate=ErrorState.UNAVAILABLE)
        # prepare text
        state = (int(cbstate.value) > 0) * (1 + (int(cbstate.value) > 1) + (int(cbstate.value) > MAXBOOK))
        parameters = (
            connector.get_user_field(uid, field='specname'),
            ev['activity_title'],
            ev['showtime'].strftime('%d/%m/%Y'),
            ev['showtime'].strftime('%H:%M'),
        ) if state < 2 else (
            connector.get_user_field(uid, field='specname'),
            cbstate.value,
            ev['activity_title'],
            ev['showtime'].strftime('%d/%m/%Y'),
            ev['showtime'].strftime('%H:%M'),
        ) if state == 2 else (
            connector.get_user_field(uid, field='specname'),
            cbstate.value,
        )
        TEXT = self.text['MESSAGE', f'{cbprev.button}_CONFIRM', state] % parameters
        # prepare keyboard
        kbd = build_inline([
            {
                self.text['BUTTON', 'CONFIRM', 1]: CallbackData.BOOK_ACCEPT if int(cbstate.value) < MAXBOOK + 1 else {'url': f'https://t.me/{BOT_ADMIN_USERNAME}'},     # NOTE is it possible to handle this button?
                self.text['BUTTON', 'CONFIRM', 0]: f'{cbprev.button}:{CallbackData.BACK}'
            },
            {self.text['BUTTON', 'TO_MAIN_MENU']: CallbackData.MAIN}
        ])
        # update context
        context.user_data['action_params'] = {
            'activity_id': cbprev.value,
            'quantity': cbstate.value
        }
        # push message
        context.user_data['last_messages'] = [query.message.edit_text(TEXT, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)]
        return ConversationState.MENU
    
    @answer
    @parse_parameters
    def book_result(self, query, context, cbstate=None, *, cbprev, uid, connector, evfilter):
        # clean part of context
        action_params = context.user_data.pop('action_params')
        print(uid, action_params)
        # request event information
        ev = connector.get_events(evfilter, uid=uid, eid=action_params['activity_id'])
        if not ev:
            return self.direct_switch(query, context, target=CallbackData.ERROR, errstate=ErrorState.UNAVAILABLE)
        # NOTE check SQL-side?        
        if int(ev['left_places']) >= int(action_params['quantity']):
            result = connector.set_registration(uid, action_params['activity_id'], action_params['quantity'])
        else:
            return self.direct_switch(query, context, target=CallbackData.ERROR, errstate=ErrorState.BOOK_DECLINED)

        breakpt = 4
        # TODO 
        return self.direct_switch(query, context, target=CallbackData.MAIN)

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
    def direct_switch(self, query, context, *, target, errstate=ErrorState.UNKNOWN):
        """ Switch to menu sheet directly
            BE CAREFUL: ALL SHEETS EXCEPT MAIN REQUIRE CALLBACK-HISTORY OR CONTEXT PARAMETERS.
            IT IS HIGHLY RECOMMENDED NOT TO SWITCH TO HIGH-LEVEL SHEETS
        """
        if target == CallbackData.MAIN:
            return self.main(query, context)
        elif target in (CallbackData.ANNOUNCE, CallbackData.MYBOOKING, CallbackData.SERVICE):
            query.data = target
            return self.available_activities(query, context)
        elif target in (CallbackData.GOODBYE, CallbackData.ERROR):
            pass    # keep parameters
        else:
            target = CallbackData.ERROR
            errstate = ErrorState.UNKNOWN
        # otherwise clear and close conversation
        self.__delete_messages(context)
        context.user_data.clear()
        kbd = build_reply([[self.text['BUTTON', 'HELLO']]], one_time_keyboard=True, resize_keyboard=True)
        context.user_data['last_messages'] = [query.message.reply_text(self.text['MESSAGE', target, errstate if target == CallbackData.ERROR else '@random'], reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)]
        return ConversationState.END
