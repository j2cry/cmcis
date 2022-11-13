import logging
import os
import pathlib
import configparser
import keyring
from telegram import ParseMode
from telegram.ext import Updater, ConversationHandler, MessageHandler
from telegram.ext.filters import Filters
from aux import ConversationState, TGText, TGMenu, build_menu, save_report
from bot_connector import BotConnector

# TODO logging: replace print with log
# # init logger
# logging.basicConfig(
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     level=logging.INFO
# )


# read configuration
CONFIG_FILE = pathlib.Path('my.cnf').absolute()
config = configparser.ConfigParser()
config.read(CONFIG_FILE.as_posix())


def debugger(query, context, backward=None):
    """ For manual testing new features or development """
    query.message.reply_text('DEBUG ACTION')
    print(context)
    print(type(context))
    print(type(query))

    # context.bot.send_message(1474200050, 'this message was sent via user id')   # ferra
    # context.bot.send_message(1078182637, 'this message was sent via user id')


def start(query, context, backward=None):
    """ Init conversation """
    user = query.message.from_user
    context.user_data.clear()
    # init SQL connector
    connector = BotConnector(dbname=config['DATABASE']['name'],
                             username=config['DATABASE']['user'],
                             schema=config['DATABASE']['schema'],
                             host=config['DATABASE']['host'],
                             port=config['DATABASE']['port'])
    context.user_data['connector'] = connector
    connector.set_user(user['id'], username=user['username'], first_name=user['first_name'], last_name=user['last_name'])
    admin_status = connector.get_user_admin(user['id'])
    print(f'admin status: {admin_status}')

    # build menu
    main_menu = build_menu([
        [TGMenu.ANNOUNCE, TGMenu.PERSONAL],
        [TGMenu.ADMIN_INFO, TGMenu.DEBUG] if admin_status else [],
        [TGMenu.GOODBYE]
    ], resize_keyboard=True)

    # query.message.reply_text(backward if backward else TGText.WELCOME.replace('$name', user['first_name']), reply_markup=main_menu)   # personalized welcome message
    query.message.reply_text(backward if backward else TGText.WELCOME, reply_markup=main_menu, parse_mode=ParseMode.MARKDOWN)   # welcome message
    return ConversationState.MAIN_MENU

def handle_main_menu(query, context, use_backward=False):
    """ Show global or personal announces """
    user = query.message.from_user
    text = backward if use_backward and (backward := context.user_data.get('backward')) else query.message.text
    admin_status = context.user_data['connector'].get_user_admin(user['id'])
    
    # define UI parameters
    if text == TGMenu.ANNOUNCE:
        EVENT_TEXT = TGText.EVENTS
        NO_EVENTS_TEXT = TGText.NO_EVENTS
    elif text == TGMenu.PERSONAL:
        EVENT_TEXT = TGText.MY_EVENTS
        NO_EVENTS_TEXT = TGText.NO_MY_EVENTS
    elif (text == TGMenu.ADMIN_INFO) and admin_status:
        print('ADMIN COMMAND')
        EVENT_TEXT = f'{TGText.ADMIN_EVENTS}'
        NO_EVENTS_TEXT = TGText.NO_EVENTS
    elif text == TGMenu.GOODBYE:
        print('END CONVERSATION: GOODBYE')
        start_menu = build_menu([[TGText.HELLO]], resize_keyboard=True)
        query.message.reply_text(TGText.END, reply_markup=start_menu)
        return ConversationHandler.END
    elif text == TGMenu.DEBUG:
        print('DEBUG ACTION')
        debugger(query, context, backward=text)
        return ConversationState.MAIN_MENU
    else:   # any other message
        print('END CONVERSATION: ERROR')
        # TODO logger code
        return start(query, context)

    # request events and check its length
    events = context.user_data['connector'].get_events(text, uid=user['id'])
    if not len(events):        # back to parent menu
        # TODO logger code
        print('NO EVENTS FOUND')
        return start(query, context, backward=NO_EVENTS_TEXT)
    
    # when all checks passed - save backward
    context.user_data['backward'] = text

    # collect events for context TODO: display free places on keyboard
    ev_names = [f'{ev.formatted_title(multirow=True)}' for ev in events]     # collect button names    NOTE: NAMES COLLISION !!!
    context.user_data['events'] = dict(zip(ev_names, events))       # update user context
    # build events menu and store it
    menu_items = [*list(map(lambda x: [x], ev_names)), [TGMenu.BACK]]
    announce_menu = build_menu(menu_items, resize_keyboard=True)
    # show message
    query.message.reply_text(EVENT_TEXT, reply_markup=announce_menu)
    return ConversationState.SELECT_EVENT


def handle_event_choice(query, context):
    """ Show event info and choice request """
    user = query.message.from_user
    text = query.message.text
    backward = context.user_data.get('backward')
    admin_status = context.user_data['connector'].get_user_admin(user['id'])

    if text == TGMenu.BACK:
        return start(query, context, backward=TGText.MENU)
    # on events not in context or event is invalid
    if not (event := context.user_data.get('events').get(text)):
        # TODO logger code
        # return start(query, context, backward=TGText.ERROR)       # drop menu        
        query.message.reply_text(TGText.ERROR)      # backward menu
        return handle_main_menu(query, context, use_backward=True)

    # update context
    context.user_data['selected_event'] = event
    # analyse backward and show announce/additional info
    # if (backward != TGMenu.ADMIN_INFO):
    if (backward == TGMenu.ANNOUNCE):        
        if event['info']:
            query.message.reply_text(event['info'], reply_markup=None, parse_mode=ParseMode.MARKDOWN)
        query.message.reply_text(TGText.FREE_PLACES % event.free_places, reply_markup=None, parse_mode=ParseMode.MARKDOWN)
    
    # build choice event menu
    accept_menu = build_menu([[TGText.YES, TGText.NO]], resize_keyboard=True)
    if admin_status and (backward == TGMenu.ADMIN_INFO):
        # request info
        rawreport = context.user_data['connector'].get_visitors_info(event['activity_id'])
        if rawreport:
            context.user_data['report'] = rawreport
        else:
            query.message.reply_text(TGText.NO_REGISTRATIONS)      # backward menu
            return handle_main_menu(query, context, use_backward=True)
        EVENT_TEXT = TGText.ADMIN_REQUEST
    elif event.isregistred(user['id']):
        EVENT_TEXT = TGText.ALREADY_REGISTRED
    else: 
        EVENT_TEXT = TGText.NOT_YET_REGISTRED
    query.message.reply_text(EVENT_TEXT, reply_markup=accept_menu)
    return ConversationState.SELECT_ACTION


def handle_action_choice(query, context):
    user = query.message.from_user
    text = query.message.text
    backward = context.user_data.get('backward')
    admin_status = context.user_data['connector'].get_user_admin(user['id'])

    if not (event := context.user_data.get('selected_event')):
        # TODO logger code - this would never appear
        return start(query, context, backward=TGText.ERROR)     # startup menu
        # query.message.reply_text(TGText.ERROR)      # backward menu
        # return handle_main_menu(query, context, use_backward=True)

    if text == TGMenu.ACCEPT:
        EVENT_TITLE = event.formatted_title(multirow=False)
        if admin_status and (backward == TGMenu.ADMIN_INFO):
            print('DOWNLOAD FILE')
            EVENT_TEXT = f'{TGText.DOWNLOAD} {EVENT_TITLE}'
            filename = pathlib.Path('reports').joinpath(event.filename).as_posix()
            save_report(filename, context.user_data['report'])
            context.user_data.pop('report')
            # send in chat
            with open(filename, 'rb') as file:
                query.message.reply_document(file)
            # remove file from disk
            os.remove(filename)
        else:
            updated = not event.isregistred(user['id'])
            context.user_data['connector'].set_registration(user['id'], event['activity_id'], updated)

            EVENT_TEXT = f'{TGText.REGISTED_ACCEPT} {EVENT_TITLE}.' if updated else f'{TGText.REGISTER_CANCEL} {EVENT_TITLE}.'        
        query.message.reply_text(EVENT_TEXT)
    else:
        query.message.reply_text(TGText.ACTION_CANCELED)

    # 1-step backward: clean context
    context.user_data.pop('selected_event', None)
    # query.message.reply_text(TGText.ERROR)      # backward menu
    return handle_main_menu(query, context, use_backward=True)
    # return start(query, context)


if __name__ == '__main__':
    # init bot updater
    updater = Updater(token=keyring.get_password('telegram', 'botuser'))
    dispatcher = updater.dispatcher
    # init handlers
    conversation_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.text, start)],
        states={    # conversation states dictionary
            ConversationState.MAIN_MENU: [
                MessageHandler(Filters.text, handle_main_menu)
            ],
            ConversationState.SELECT_EVENT: [
                MessageHandler(Filters.text, handle_event_choice),
            ],
            ConversationState.SELECT_ACTION: [
                MessageHandler(Filters.text, handle_action_choice),
            ]
        },
        fallbacks=[MessageHandler(Filters.text, start)]
    )
    dispatcher.add_handler(conversation_handler)

    # run bot
    updater.start_polling()
    updater.idle()
