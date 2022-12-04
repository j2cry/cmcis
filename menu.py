from typing import List, Dict
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ParseMode
from states import ConversationState, MenuCallbackData, ButtonCallbackData, ErrorState, CallbackState
from functools import wraps


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
        """ Parse common context parameters """
        @wraps(method)
        def wrapper(self, query, context, **kwargs):
            # request general parameters
            parameters = {
                'uid': context.user_data['uid'],
                'connector': context.user_data['connector'],
                'cbstate': CallbackState(*query.data.split(':') if hasattr(query, 'data') else [MenuCallbackData.MAIN])      # target menu callback state
            }
            return method(self, query, context, **parameters, **kwargs)
        return wrapper

    @answer
    @parse_parameters
    def main(self, query, context, *, uid, connector, cbstate, **kwargs):
        """ Show main menu """
        # parse additional required context parameters
        is_admin = connector.get_user_field(uid, field='is_admin')
        cvstate = context.user_data['cvstate']      # conversation state
        # build keyboard
        kbd = build_inline([
            {self.text['BUTTON', 'EVENTS']: f'{MenuCallbackData.EVLIST}:{ButtonCallbackData.EVENTS}'},
            {self.text['BUTTON', 'BOOKING']: f'{MenuCallbackData.EVLIST}:{ButtonCallbackData.BOOKING}'},
            {self.text['BUTTON', 'SERVICE']: f'{MenuCallbackData.EVLIST}:{ButtonCallbackData.SERVICE}'} if is_admin else {},
            {self.text['BUTTON', 'ABOUT']: f'{ButtonCallbackData.ABOUT}'},
            {self.text['BUTTON', 'GOODBYE']: f'action:{ButtonCallbackData.GOODBYE}'},
        ])
        self.__delete_messages(context)
        infotext = self.text['MESSAGE', 'WELCOME', 2] if (cbstate.button == ButtonCallbackData.TO_MAIN_MENU) else self.text['MESSAGE', 'WELCOME', cvstate] % context.user_data['specname']
        context.user_data['last_messages'] = [query.message.reply_text(infotext, reply_markup=kbd)]
        return ConversationState.BODY        

    @answer
    @parse_parameters
    def available_activities(self, query, context, *, uid, connector, cbstate, **kwargs):
        """ Show available activities """
        # setup context
        button = cbstate.button if cbstate.button != ButtonCallbackData.BACK else context.user_data['evfilter']
        context.user_data['evfilter'] = button
        # request actual events depending on pressed button
        events = connector.get_events(button, uid=uid)            # TODO доработать запрос БД
        # print(f'button: {cbtarget.button}', *events, sep='\n')        # DEBUG FEATURE
        kbd = build_inline([        # build inline in no events found
            {self.text['BUTTON', 'TO_RELATED_CHANNEL']: f'{MenuCallbackData.MAIN}:{ButtonCallbackData.TO_MAIN_MENU}'},     # TODO link to channel
            {self.text['BUTTON', 'TO_MAIN_MENU']: f'{MenuCallbackData.MAIN}:{ButtonCallbackData.TO_MAIN_MENU}'}
        ]) if not events else None
        # push message
        evlist = [query.message.edit_text(self.text['MESSAGE', 'EVENTS', bool(events)], reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)]
        # collect events list
        for num, ev in enumerate(events, 1):
            kbd = build_inline([
                {
                    self.text['BUTTON', 'MORE']: f'{MenuCallbackData.EVCARD}:{ButtonCallbackData.MORE}:{ev["activity_id"]}',
                    self.text['BUTTON', 'BOOK', bool(ev['booked'])]: f'{MenuCallbackData.EVBOOK}:{ButtonCallbackData.BOOK}:{ev["activity_id"]}'
                },
                {self.text['BUTTON', 'TO_MAIN_MENU']: f'{MenuCallbackData.MAIN}:{ButtonCallbackData.TO_MAIN_MENU}'} if num == len(events) else {},
            ])
            # TODO настроить отображение карточки анонса
            infocard = f"*{ev['activity_title']}*\n" \
                        f"{ev['showtime'].strftime('%d/%m/%Y %H:%M')}, {ev['place_title']}\n" \
                        f"{(ev['announce']) if ev['announce'] else ''}" \
                        f""
                        # TODO текст по state
            evlist.append(query.message.reply_text(infocard, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN))
        context.user_data['last_messages'] = evlist
        return ConversationState.BODY

    @answer
    @parse_parameters
    def activity_infocard(self, query, context, *, uid, connector, cbstate, **kwargs):
        """ Show activity large infocard """
        self.__delete_messages(context)
        # request event information depending on pressed button
        ev = connector.get_events(context.user_data.get('evfilter', ButtonCallbackData.EVENTS), uid=uid, eid=cbstate.value)
        if not ev:
            return self.raise_error(query, context, state=ErrorState.UNAVAILABLE)
        # prepare infocard
        infocard = f"*{ev['activity_title']}*" \
                    f"{ev['showtime'].strftime('%d/%m/%Y %H:%M')}, {ev['place_title']}\n" \
                    f"{ev['addr']}\n" \
                    f"{ev['info']}" \
                    f""
                    # TODO количество мест
        # prepare keyboard
        kbd = build_inline([
            {self.text['BUTTON', 'BOOK', bool(ev['booked'])]: f'{MenuCallbackData.EVBOOK}:{ButtonCallbackData.BOOK}:{ev["activity_id"]}'},
            {self.text['BUTTON', 'SHOWMAP']: f'{MenuCallbackData.EVMAP}:{ButtonCallbackData.SHOWMAP}:{ev["activity_id"]}'},
            {self.text['BUTTON', 'BACK']: f'{MenuCallbackData.EVLIST}:{ButtonCallbackData.BACK}'},
            {self.text['BUTTON', 'TO_MAIN_MENU']: f'{MenuCallbackData.MAIN}:{ButtonCallbackData.TO_MAIN_MENU}'}
        ])
        # push message
        context.user_data['last_messages'] = [query.message.reply_text(infocard, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)]
        return ConversationState.BODY

    @answer
    @parse_parameters
    def showmap(self, query, context, *, uid, connector, cbstate, **kwargs):
        """ Show address & map """
        # request event information depending on pressed button
        ev = connector.get_events(context.user_data.get('evfilter', ButtonCallbackData.EVENTS), uid=uid, eid=cbstate.value)
        if not ev:
            return self.raise_error(query, context, state=ErrorState.UNAVAILABLE)
        # prepare infocard
        infocard = f"Тут будет карта."      # TODO map link
        # prepare keyboard
        kbd = build_inline([
            {self.text['BUTTON', 'BACK']: f'{MenuCallbackData.EVCARD}:{ButtonCallbackData.BACK}:{ev["activity_id"]}'},
            {self.text['BUTTON', 'TO_MAIN_MENU']: f'{MenuCallbackData.MAIN}:{ButtonCallbackData.TO_MAIN_MENU}'}
        ])
        # push message
        context.user_data['last_messages'] = [query.message.edit_text(infocard, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)]
        return ConversationState.BODY

    @answer
    @parse_parameters
    def book(self, query, context, cbstate, **kwargs):
        """ Booking sheet """
        print(f'target callback: ', *cbstate)
        return self.raise_error(query, context, state=ErrorState.INDEV)




    def action(self, update, context):
        """ Handle actions """
        if not (query := update.callback_query):
            query = update
        else:
            query.answer()
        # button callback data: previous and target
        cbprev = context.user_data.get('cbstate', CallbackState())        # previous state
        cbtarget = CallbackState(*query.data.split(':') if hasattr(query, 'data') else ['action', None, None])       # target state
        callback = getattr(self, f'_{self.__class__.__name__}__{cbtarget.button}_callback', self.raise_error)
        return callback(query, context)

    def __delete_messages(self, context):
        evlist = context.user_data.get('last_messages', None)
        if not evlist:
            return
        for ev in evlist:
            ev.delete()
        context.user_data['last_messages'] = []

    @answer
    def raise_error(self, query, context, state=ErrorState.UNKNOWN):
        self.__delete_messages(context)
        context.user_data.clear()
        kbd = build_reply([[self.text['BUTTON', 'HELLO']]], one_time_keyboard=True, resize_keyboard=True)
        context.user_data['last_messages'] = [query.message.reply_text(self.text['MESSAGE', 'ERROR', state], reply_markup=kbd)]
        return ConversationState.END

    def __goodbye_callback(self, update, context):
        update.answer()
        self.__delete_messages(context)
        context.user_data.clear()
        kbd = build_reply([[self.text['BUTTON', 'HELLO']]], one_time_keyboard=True, resize_keyboard=True)
        context.user_data['last_messages'] = [update.message.reply_text(self.text['MESSAGE', 'GOODBYE', '@random'], reply_markup=kbd)]
        # context.job_queue.run_once(lambda _: message.delete(), 2)     # run delayed task
        return ConversationState.END
    
