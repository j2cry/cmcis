import re
import qrcode
from io import BytesIO
from typing import List, Dict
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ParseMode
from telegram.utils.helpers import create_deep_linked_url
from states import ConversationState, CallbackData, ErrorState, CallbackState, HistoryState
from functools import wraps
from inspect import Parameter, signature


def build_reply(schema: List[List], **kwargs):
    """ Create telegram chat menu as keyboard from list of lists with button names """
    return ReplyKeyboardMarkup(schema, **kwargs)

def build_inline(schema: List[Dict], **kwargs):
    """ Create telegram chat menu as inline keyboard from list of dictss with button names """
    return InlineKeyboardMarkup([[InlineKeyboardButton(k, **v) if isinstance(v, dict) else InlineKeyboardButton(k, callback_data=v)
                                for k, v in row.items()] for row in schema], **kwargs)


def collect_card(*parts, first_bold=True):
    prepared = []
    for p in parts:
        if isinstance(p, (tuple, list)):
            if p[0]:
                prepared.append(p[1] % p[0])
        elif p:
            prepared.append(p)
    if prepared and first_bold:
        prepared[0] = f'*{prepared[0]}*'
    return '\n'.join(prepared)


class MenuHandler:
    """ Menu interactions handler """
    def __init__(self, text, connector):
        self.text = text
        self.connector = connector

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
            # update menu callback state
            # cbstate = CallbackState(*query.data.split(':') if hasattr(query, 'data') else [CallbackData.MAIN])    # target callback state
            cbstate = CallbackState(*query.data.split(':') if hasattr(query, 'data') else [])    # target callback state
            history = context.user_data.get('history', HistoryState([CallbackState(CallbackData.MAIN), ]))
            # update history
            if cbstate.value and cbstate.value.startswith(CallbackData.BACK):
                step = (-int(v.group(0)) + 1) if (v := re.search(r'\d+', cbstate.value)) else -1
                history = HistoryState(history[:step])
            elif cbstate.button == CallbackData.MAIN:
                history = HistoryState([cbstate, ])
            elif cbstate.button:
                history.append(cbstate)
            context.user_data['history'] = history
            # collect required KEYWORD_ONLY parameters from context or use defaults
            required_kw = {pname: context.user_data.get(pname, pvalue.default if pvalue.default != Parameter.empty else None)
                           for pname, pvalue in signature(method).parameters.items() if pvalue.kind == Parameter.KEYWORD_ONLY}

            # NOTE collect POSITIONAL_OR_KEYWORD parameters ?
            print('menu history', *history, '-' * 25, sep='\n')

            result = method(self, query, context, **required_kw)
            return result
        return wrapper

    def start(self, update, context):
        """ Initialize conversation """
        update.message.delete()
        user = update.message.from_user
        context.user_data['uid'] = user['id']
        # context.user_data['connector'] = connector

        # request user data
        if not (specname := self.connector.get_user_field(user['id'], field='specname')):
            context.user_data['last_messages'] = [update.message.reply_text(self.text['MESSAGE', 'FIRST_MET'], reply_markup=None, parse_mode=ParseMode.MARKDOWN)]   # NOTE Is it possible to hide keyboard ?
            return ConversationState.FIRST_MET

        context.user_data['specname'] = specname
        context.user_data['nickname'] = user['username']
        context.user_data['cvstate'] = 1      # user exists state

        # return self.check_ticket(update, context) if hasattr(context, 'args') else self.main(update, context)
        is_admin = self.connector.get_user_field(user['id'], field='is_admin')
        return self.check_ticket(update, context) if context.args and is_admin else self.main(update, context)

    def first_met(self, update, context):
        """ User first met: `specname` input """
        user = update.message.from_user
        specname = update.message.text[:100]
        # collect user data and push to database
        data = {
            'specname': specname,
            'username': user['username'],
            'first_name': user['first_name'],
            'last_name': user['last_name'],
        }
        self.connector.set_user(user['id'], **data)
        context.user_data['specname'] = specname
        context.user_data['cvstate'] = 0      # new user state
        update.message.delete()
        return self.main(update, context)

    @parse_parameters
    def message(self, query, context, *, history):
        """ Handle direct message """
        value = query.message.text
        try:
            query.message.delete()
        except:
            print(f'It seems, this message was deleted by the user: {query.message.message_id}')
        if history.current.button == CallbackData.BOOK:
            places = ''.join(digits if (digits := re.findall(r'\d', value)) else ['0'])
            history.append(CallbackState(CallbackData.BOOK_CONFIRM, places))
            return self.book_confirm(query, context)
        return ConversationState.MENU

    @answer
    @parse_parameters
    def main(self, query, context, *, history, uid):
        """ Show main menu """
        # parse additional required context parameters
        is_admin = self.connector.get_user_field(uid, field='is_admin')
        cvstate = context.user_data['cvstate']      # conversation state
        # build keyboard
        kbd = build_inline([
            {self.text['BUTTON', 'ANNOUNCE']: CallbackData.ANNOUNCE},
            {self.text['BUTTON', 'BOOKING']: CallbackData.MYBOOKING},
            # {self.text['BUTTON', 'SERVICE']: CallbackData.SERVICE} if is_admin else {},
            {self.text['BUTTON', 'ABOUT']: CallbackData.ABOUT},
            {self.text['BUTTON', 'GOODBYE']: CallbackData.GOODBYE},
            # {'debug action': 'DEBUG'} if is_admin else {},
        ])
        self.__delete_messages(context)
        infotext = self.text['MESSAGE', 'WELCOME', 2] if (history.prev.button == CallbackData.MAIN) else self.text['MESSAGE', 'WELCOME', cvstate] % context.user_data['specname']
        context.user_data['last_messages'] = [query.message.reply_text(infotext, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)]
        return ConversationState.MENU

    @answer
    @parse_parameters
    def available_activities(self, query, context, *, history, uid):
        """ Show available activities """
        # setup context
        context.user_data['evfilter'] = history.current.button
        # request actual events depending on pressed button
        events = self.connector.get_events(history.current.button, uid=uid)
        booked = [ev for ev in events if ev['quantity']]
        # build zero-events keyboard
        kbd = build_inline([
            {self.text['BUTTON', 'TO_RELATED_CHANNEL']: {'url': self.connector.settings['RELATED_CHANNEL']}},      # NOTE is it possible to handle this button?
            {self.text['BUTTON', 'TO_MAIN_MENU']: CallbackData.MAIN}
        ]) if not events else build_inline([
            {self.text['BUTTON', 'TO_ANNOUNCE']: CallbackData.ANNOUNCE},
            {self.text['BUTTON', 'TO_MAIN_MENU']: CallbackData.MAIN}
        ]) if not booked and (history.current.button == CallbackData.MYBOOKING) else None
        # setup zero-events text
        if history.current.button == CallbackData.ANNOUNCE:
            TEXT = self.text['MESSAGE', 'ANNOUNCE', bool(events)]
        elif history.current.button == CallbackData.MYBOOKING:      # for BOOKING: check announces
            TEXT = self.text['MESSAGE', 'BOOKS', bool(booked) if events else 2]
            events = booked
        # push message
        evlist = [query.message.edit_text(TEXT, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)]
        # collect events list
        for num, ev in enumerate(events, 1):
            kbd = build_inline([
                {
                    self.text['BUTTON', 'MORE']: f'{CallbackData.MORE}:{ev["activity_id"]}',
                    self.text['BUTTON', 'BOOK', bool(ev['quantity'])]: f'{CallbackData.BOOK}:{ev["activity_id"]}'
                },
                # {self.text['BUTTON', 'BACK']: f'{context.user_data["history"][-2].button}'} if num == len(events) else {},    # BACK button example
                {self.text['BUTTON', 'TO_MAIN_MENU']: CallbackData.MAIN} if num == len(events) else {},
            ])
            # TODO настроить отображение карточки анонса
            TEXT = f"*{ev['activity_title']}*\n" \
                   f"{ev['showtime'].strftime('%d/%m/%Y %H:%M')}, {ev['place_title']}\n" \
                   f"{(ev['announce']) if ev['announce'] else ''}\n" \
                   f"{self.text['FILLER', 'LEFT_PLACES', ev['left_places'] > 0] % ((ev['left_places'],) if ev['left_places'] > 0 else ())}\n" \
                   f""
                   # TODO текст по state: про места, очередь, бронирование итп
            evlist.append(query.message.reply_text(TEXT, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN))
        context.user_data['last_messages'] = evlist
        return ConversationState.MENU

    @answer
    @parse_parameters
    def service_activities(self, query, context, *, history, uid):
        """ Manage actual activities """
        # setup context
        context.user_data['evfilter'] = history.current.button
        # request actual events depending on pressed button
        events = self.connector.get_events(history.current.button, uid=uid)
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
    def activity_info(self, query, context, *,  history, uid, evfilter):
        """ Show activity large infocard """
        self.__delete_messages(context)
        # request event information depending on pressed button
        ev = self.connector.get_events(evfilter, uid=uid, eid=history.current.value)
        if not ev:
            return self.direct_switch(query, context, target=CallbackData.ERROR, errstate=ErrorState.UNAVAILABLE)
        # prepare infocard
        TEXT = f"*{ev['activity_title']}*\n" \
               f"{ev['showtime'].strftime('%d/%m/%Y %H:%M')}, {ev['place_title']}\n" \
               f"{ev['addr']}\n" \
               f"{ev['activity_info']}\n" \
               f"{self.text['FILLER', 'LEFT_PLACES', ev['left_places'] > 0].agree_with_number(*(ev['left_places'],) if ev['left_places'] > 0 else ())}"
            #    f"{self.text['FILLER', 'LEFT_PLACES', ev['left_places'] > 0] % ((ev['left_places'],) if ev['left_places'] > 0 else ())}"
        # prepare keyboard
        kbd = build_inline([
            {self.text['BUTTON', 'BOOK', bool(ev['quantity'])]: f'{CallbackData.BOOK}:{ev["activity_id"]}'},
            {self.text['BUTTON', 'SHOWMAP']: f'{CallbackData.SHOWMAP}:{ev["activity_id"]}'},
            {self.text['BUTTON', 'SHOWTICKET']: f'{CallbackData.SHOWTICKET}:{ev["activity_id"]}'} if ev['quantity'] else {},       # TODO
            {self.text['BUTTON', 'BACK']: f'{history.prev.button}:{CallbackData.BACK}'},
            {self.text['BUTTON', 'TO_MAIN_MENU']: CallbackData.MAIN}
        ])
        # push message
        context.user_data['last_messages'] = [query.message.reply_text(TEXT, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)]
        return ConversationState.MENU

    @answer
    @parse_parameters
    def showmap(self, query, context, *, history, uid, evfilter):
        """ Show address & map """
        # request event information depending on menu section
        ev = self.connector.get_events(evfilter, uid=uid, eid=history.current.value)
        if not ev:
            return self.direct_switch(query, context, target=CallbackData.ERROR, errstate=ErrorState.UNAVAILABLE)
        TEXT = collect_card(ev['place_title'],
                            ev['place_info'],
                            ev['addr'],
                            (ev['maplink'], self.text["FILLER", "SHOWMAP"]),
                            )
        # prepare keyboard
        kbd = build_inline([
            {self.text['BUTTON', 'BACK']: f'{history.prev.button}:{CallbackData.BACK}'},
            {self.text['BUTTON', 'TO_MAIN_MENU']: CallbackData.MAIN}
        ])
        # push message
        context.user_data['last_messages'] = [query.message.edit_text(TEXT, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)]   # disable_web_page_preview
        return ConversationState.MENU

    @answer
    @parse_parameters
    def showticket(self, query, context, *, history, uid, evfilter):
        """ Show ticket info """
        # request event information about selected activity
        ev = self.connector.get_events(evfilter, uid=uid, eid=history.current.value)
        if not ev:
            return self.direct_switch(query, context, target=CallbackData.ERROR, errstate=ErrorState.UNAVAILABLE)
        if ev['quantity'] == 0:
            return self.direct_switch(query, context, target=CallbackData.ERROR, errstate=ErrorState.FORBIDDEN)
        # generate ticket
        ticket_link = create_deep_linked_url(context.bot.username, f'{uid}_{ev["activity_id"]}')
        image = qrcode.make(ticket_link)
        # convert PIL to bytes
        bimage = BytesIO()
        image.save(bimage, 'JPEG')
        bimage.seek(0)

        # prepare keyboard
        kbd = build_inline([
            {self.text['BUTTON', 'BACK']: f'{history.prev.button}:{CallbackData.BACK}'},
            {self.text['BUTTON', 'TO_MAIN_MENU']: CallbackData.MAIN}
        ])
        # push message
        self.__delete_messages(context)
        context.user_data['last_messages'] = [query.message.reply_photo(bimage, caption='', reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)]
        bimage.close()
        return ConversationState.MENU
        # return self.direct_switch(query, context, target=CallbackData.ERROR, errstate=ErrorState.INDEV)

    @answer
    @parse_parameters
    def book(self, query, context, *, history, uid, evfilter):
        """ Booking sheet """
        # request event information depending on menu section
        ev = self.connector.get_events(evfilter, uid=uid, eid=history.current.value)
        if not ev:
            return self.direct_switch(query, context, target=CallbackData.ERROR, errstate=ErrorState.UNAVAILABLE)
        # prepare infocard
        parameters = (
            self.connector.get_user_field(uid, field='specname'),
            ev['activity_title'],
            ev['showtime'].strftime('%d/%m/%Y'),
            ev['showtime'].strftime('%H:%M'),
            ev['place_title'],
        )
        # left_places_state = ev['left_places'] if ev['left_places'] < 2 else 2
        left_places_state = 0 if ev['left_places'] < 0 else 2 if ev['left_places'] > 2 else ev['left_places']
        # TEXT without BOOK_IS_CONFIRMED text
        TEXT = self.text['MESSAGE', 'BOOK_PROCESS_HEAD', ev['quantity'] > 0] % parameters + \
               f" {self.text['MESSAGE', 'BOOK_PROCESS_BODY', left_places_state].agree_with_number(*(ev['left_places'],) if ev['left_places'] > 1 else ())}" + \
               (f"\n{self.text['MESSAGE', 'BOOK_PROCESS_BODY', 3].agree_with_number(ev['quantity'])}" if ev['quantity'] else "") + \
               f" {self.text['MESSAGE', 'BOOK_PROCESS_FINAL', ev['quantity'] > 0]}"
        # TEXT = self.text['MESSAGE', 'BOOK_PROCESS_HEAD', ev['quantity'] > 0] % parameters + \
        #        f" {self.text['MESSAGE', 'BOOK_PROCESS_BODY', left_places_state].agree_with_number(e*(ev['left_places'],) if ev['left_places'] > 1 else ())}" + \
        #        (f"\n{self.text['MESSAGE', 'BOOK_PROCESS_BODY', 3].agree_with_number(ev['quantity'])} {self.text['MESSAGE', 'BOOK_IS_CONFIRMED', ev['confirmed']]}" if ev['quantity'] else "") + \
        #        f" {self.text['MESSAGE', 'BOOK_PROCESS_FINAL', ev['quantity'] > 0]}"
        # prepare keyboard
        MAXBOOK = int(self.connector.settings['MAXBOOK'])
        one_ticket_state = 2 * bool(ev['left_places'] + ev['quantity'] > 1) + (ev['left_places'] == 1 and not ev['quantity'])
        # available_range = range(1, min(MAXBOOK + 1, ev['left_places'] + ev['quantity']) + 1)
        available_range = range(1, min(MAXBOOK, ev['left_places'] + ev['quantity']) + 1)
        kbd = build_inline([
            {} if not one_ticket_state else      # booked 1 place and no places left -> don't show book choises
            {self.text['BUTTON', 'BOOK_QUANTITY']: f'{CallbackData.BOOK_CONFIRM}:1'} if one_ticket_state == 1 else
            {n: f'{CallbackData.BOOK_CONFIRM}:{n}' for n in available_range if n != ev['quantity']},

            {self.text['BUTTON', 'BOOK_QUANTITY', 2]: f'{CallbackData.BOOK_CONFIRM}:0'} if ev['quantity'] else {},
            {self.text['BUTTON', 'BACK']: f'{history.prev.button}:{CallbackData.BACK}'},
            # {self.text['BUTTON', 'MORE']: f'{CallbackData.MORE}:{ev["activity_id"]}'},      # NOTE backup
            {self.text['BUTTON', 'TO_MAIN_MENU']: CallbackData.MAIN}
        ])
        # push message
        self.__delete_messages(context)
        context.user_data['last_messages'] = [query.message.reply_text(TEXT, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)]
        return ConversationState.MENU

    @answer
    @parse_parameters
    def book_confirm(self, query, context, *, history, uid, evfilter):
        """ Confirm booking """
        # request event information depending on menu section
        ev = self.connector.get_events(evfilter, uid=uid, eid=history.prev.value)
        if not ev:
            return self.direct_switch(query, context, target=CallbackData.ERROR, errstate=ErrorState.UNAVAILABLE)
        MAXBOOK = int(self.connector.settings['MAXBOOK'])
        # prepare text
        state = v if (v := int(history.current.value)) < 2 else 2
        parameters = (
            self.connector.get_user_field(uid, field='specname'),
            ev['activity_title'],
            ev['showtime'].strftime('%d/%m/%Y'),
            ev['showtime'].strftime('%H:%M'),
        ) if state < 2 else (
            self.connector.get_user_field(uid, field='specname'),
            history.current.value,
            ev['activity_title'],
            ev['showtime'].strftime('%d/%m/%Y'),
            ev['showtime'].strftime('%H:%M'),
        )
        # TEXT = self.text['MESSAGE', f'{history.prev.button}_CONFIRM', state] % parameters
        TEXT = self.text['MESSAGE', f'BOOK_CONFIRM', state].agree_with_number(*parameters)
        # prepare keyboard
        kbd = build_inline([
            {
                # self.text['BUTTON', 'CONFIRM', 1]: CallbackData.BOOK_ACCEPT if int(history.current.value) < MAXBOOK + 1 else {'url': f'https://t.me/{connector.settings["BOT_ADMIN_USERNAME"]}'},     # NOTE is it possible to handle this button?
                self.text['BUTTON', 'CONFIRM', 1]: CallbackData.BOOK_ACCEPT,
                self.text['BUTTON', 'CONFIRM', 0]: f'{history.prev.button}:{CallbackData.BACK}'
            },
            {self.text['BUTTON', 'TO_MAIN_MENU']: CallbackData.MAIN}
        ])
        # update context
        context.user_data['action_params'] = {
            'activity_id': history.prev.value,
            'quantity': history.current.value
        }
        # push message
        # context.user_data['last_messages'] = [query.message.edit_text(TEXT, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)]
        context.user_data['last_messages'] = [context.user_data['last_messages'][-1].edit_text(TEXT, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)]
        return ConversationState.MENU

    @answer
    @parse_parameters
    def book_result(self, query, context, *, history, uid, nickname, evfilter, notification={}):
        # clean part of context
        action_params = context.user_data.pop('action_params')
        # request event information
        ev = self.connector.get_events(evfilter, uid=uid, eid=action_params['activity_id'])
        if not ev:
            return self.direct_switch(query, context, target=CallbackData.ERROR, errstate=ErrorState.UNAVAILABLE)

        # NOTE check SQL-side?
        drop_book_state = int(action_params['quantity']) == 0
        if free_places_state := (int(ev['left_places']) + int(ev['quantity'])) >= int(action_params['quantity']):
            # autoconfirm = (int(action_params['quantity']) <= int(self.connector.settings['MAXBOOK'])) or (bool(ev['confirmed']) and (int(action_params['quantity']) <= ev['quantity']))
            autoconfirm = (int(action_params['quantity']) <= int(self.connector.settings['MAXBOOK'])) or (int(action_params['quantity']) <= ev['quantity'])
        else:
            autoconfirm = False

        # request admin confirmation if required
        if autoconfirm:
            # book_state = self.connector.set_registration(uid, action_params['activity_id'], action_params['quantity'], autoconfirm)     # for additional confirmation feature
            book_state = self.connector.set_registration(uid, action_params['activity_id'], action_params['quantity'])
        elif free_places_state:
            book_state = False
            parameters = (
                self.connector.get_user_field(uid, field='specname'),
                action_params['quantity'],
                ev['activity_title'],
                ev['showtime'].strftime('%d/%m/%Y'),
                ev['showtime'].strftime('%H:%M'),
            )
            TEXT = self.text['MESSAGE', 'BOOK_CONFIRM_REQUEST'].agree_with_number(*parameters)
            kbd = build_inline([
                {
                    self.text['BUTTON', 'CONFIRM', 1]: f'{CallbackData.BOOK_CONFIRM_ADMIN}:1,{uid},{ev["activity_id"]},{action_params["quantity"]}',
                    self.text['BUTTON', 'CONFIRM', 0]: f'{CallbackData.BOOK_CONFIRM_ADMIN}:0,{uid},,',
                },
                # applicant chat link
                {self.text['BUTTON', 'APPLICANT_CHAT']: {'url': CallbackData.USER_LINK[bool(nickname)] % (nickname if nickname else uid)}}
            ])
            # delete previous notification
            if ev["activity_id"] in notification:
                try:
                    notification[ev["activity_id"]].delete()
                except:
                    notification.pop(ev["activity_id"])
            notification[ev["activity_id"]] = context.bot.send_message(self.connector.settings['BOT_ADMIN_ID'], TEXT, reply_markup=kbd)
            context.user_data['notification'] = notification
        else:
            book_state = False
        # prepare text
        TEXT = self.text['MESSAGE', 'BOOK_RESULT', free_places_state + autoconfirm + book_state + drop_book_state]
        # prepare keyboard
        kbd = build_inline([
            {},
            {self.text['BUTTON', 'BACK']: f'{history[-4].button}:{CallbackData.BACK}(4)'},    # 4-step backward
            {self.text['BUTTON', 'TO_MAIN_MENU']: CallbackData.MAIN},
        ])
        # push message
        context.user_data['last_messages'] = [query.message.edit_text(TEXT, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)]
        return ConversationState.MENU

    @answer
    @parse_parameters
    def admin_confirm(self, query, context, *, history):
        """ Admin book confirmation """
        state, uid, activity_id, places = history.current.value.split(',')
        state = int(state)
        # update book confirmation
        if state:
            # request activity info for overbooking check
            if state != 2:    # 2 means force confirm
                ev = self.connector.get_events(CallbackData.ANNOUNCE, uid=uid, eid=activity_id)
                overbook = int(places) - (ev['quantity'] + ev['left_places'])
                if overbook > 0:
                    parameters = (
                        ev['activity_title'],
                        ev['showtime'].strftime('%d/%m/%Y'),
                        ev['showtime'].strftime('%H:%M'),
                        overbook
                    )
                    # prepare text
                    TEXT = self.text['MESSAGE', 'BOOK_CONFIRM_REQUEST', 1].agree_with_number(*parameters)
                    # prepare keyboard
                    kbd = build_inline([{
                        self.text['BUTTON', 'CONFIRM', 1]: f'{CallbackData.BOOK_CONFIRM_ADMIN}:2,{uid},{activity_id},{places}',
                        self.text['BUTTON', 'CONFIRM', 0]: f'{CallbackData.BOOK_CONFIRM_ADMIN}:0,{uid},,',
                    }])
                    # push message
                    query.message.edit_text(TEXT, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)
                    return ConversationState.END
            # self.connector.set_registration(uid, activity_id, value=places, confirmed=bool(state))
            self.connector.set_registration(uid, activity_id, value=places)
        try:
            query.message.delete()
        except:
            print(f'It seems, this message was deleted by the user: {query.message.message_id}')
        # backward notification
        context.bot.send_message(uid, self.text['MESSAGE', 'BOOK_CONFIRM_RESPONSE', state > 0])
        return ConversationState.END        # NOTE это сбрасывает диалог, если он был

    @parse_parameters
    def check_ticket(self, query, context, *, uid, ticketmsg):
        client_id, activity_id = context.args[0].split('_')
        # get users booking info
        ev = self.connector.get_events(CallbackData.ANNOUNCE, uid=client_id, eid=activity_id)
        if not ev:
            return self.direct_switch(query, context, target=CallbackData.ERROR, errstate=ErrorState.UNAVAILABLE)
        # redeem ticket
        redeem_state = (ev['quantity'] > 0) and self.connector.set_registration(client_id, activity_id, redeemed=True)
        if not redeem_state:
            return self.direct_switch(query, context, target=CallbackData.ERROR, errstate=ErrorState.SERVERSIDE)
        if ticketmsg:
            try:
                ticketmsg.delete()
            except:
                print(f'It seems, this message was deleted by the user: {ticketmsg}')
        # prepare text
        parameters = (
            ev['quantity'],
            ev['activity_title'],
            ev['showtime'].strftime('%d/%m/%Y'),
            ev['showtime'].strftime('%H:%M'),
        )
        # prepare text            
        TEXT = self.text['MESSAGE', 'TICKET_INFO', ev['quantity'] > 0].agree_with_number(*parameters if ev['quantity'] > 0 else ()) + \
            (f"\n{self.text['MESSAGE', 'REDEEMED']}" if ev['redeemed'] else '')
        context.user_data['ticketmsg'] = context.bot.send_message(uid, TEXT)
        return ConversationState.END

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
    def direct_switch(self, query, context, *, target, errstate=ErrorState.UNKNOWN, safemode=True):
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
