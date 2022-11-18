import logging
import pathlib
import configparser
import keyring
from telegram import ParseMode
from telegram.ext import Updater, ConversationHandler, MessageHandler, CallbackQueryHandler
from telegram.ext.filters import Filters
from aux import ConversationState, actions, build_keyboard, manage_menu
from dictionary import TGText, TGMenu
from bot_connector import BotConnector
from functools import partial

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


def debugger(query, context):
    """ For manual testing new features or development """
    query.message.reply_text('DEBUG ACTION')
    return ConversationState.MAIN_MENU


def show_start_menu(query, context, custom_text=None):
    """ Drop conversation and show start menu """
    query.message.reply_text(custom_text if custom_text else TGText.FAREWELL, reply_markup=build_keyboard([[TGMenu.HELLO]], resize_keyboard=True))
    return ConversationHandler.END


@manage_menu(level=0)
def show_main_menu(query, context, custom_text=None):
    """ Initialize conversation and show main menu """
    # initialize
    user = query.message.from_user
    context.user_data.clear()
    context.user_data['menu_tree'] = []
    # init SQL connector
    connector = BotConnector(dbname=config['DATABASE']['name'],
                             username=config['DATABASE']['user'],
                             schema=config['DATABASE']['schema'],
                             host=config['DATABASE']['host'],
                             port=config['DATABASE']['port'])
    context.user_data['connector'] = connector
    connector.set_user(user['id'], username=user['username'], first_name=user['first_name'], last_name=user['last_name'])
    admin_status = connector.get_user_admin(user['id'])
    # build main menu
    main_menu = build_keyboard([
        [TGMenu.ANNOUNCE, TGMenu.PERSONAL],
        [TGMenu.SERVICE] if admin_status else [],
        [TGMenu.DEBUG] if admin_status else [],     # NOTE DEBUG FEATURE
        [TGMenu.GOODBYE]
    ], resize_keyboard=True)

    # query.message.reply_text(backward if backward else TGText.WELCOME.replace('$name', user['first_name']), reply_markup=main_menu)   # personalized welcome message
    query.message.reply_text(custom_text if custom_text else TGText.WELCOME, reply_markup=main_menu, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)   # welcome message
    return ConversationState.MAIN_MENU


@manage_menu(level=1)
def show_select_event_menu(query, context):
    """ Build and show events list menu """
    # initialize
    menu = context.user_data['menu_tree']
    user = query.message.from_user
    step = query.message.text if len(menu) < 1 else menu[0]     # setup backward
    admin_status = context.user_data['connector'].get_user_admin(user['id'])

    if step == TGMenu.ANNOUNCE:
        POS_TEXT = TGText.PUBLIC_EVENTS
        NEG_TEXT = TGText.ZERO_PUBLIC_EVENTS
    elif step == TGMenu.PERSONAL:
        POS_TEXT = TGText.PERSONAL_EVENTS
        NEG_TEXT = TGText.ZERO_PERSONAL_EVENTS
    elif (step == TGMenu.SERVICE) and admin_status:
        POS_TEXT = f'{TGMenu.SERVICE}: {TGText.ADMIN_EVENTS.lower()}'
        NEG_TEXT = TGText.ZERO_ADMIN_EVENTS

    # request events and check its length
    events = context.user_data['connector'].get_events(step, uid=user['id'])
    if not len(events):        # back to parent menu
        # TODO logger code
        return show_main_menu(query, context, custom_text=NEG_TEXT)

    # collect events for context TODO: display free places on keyboard
    ev_names = [ev.formatted_title(multirow=True) for ev in events]     # collect button names    BUG NOTE: NAMES COLLISION !!!
    context.user_data['events'] = dict(zip(ev_names, events))       # update user context
    # build events menu
    menu_items = [*list(map(lambda x: [x], ev_names)), [TGMenu.BACK]]
    choice_event_menu = build_keyboard(menu_items, resize_keyboard=True)
    # route conversation to the next step: show event choosing menu
    query.message.reply_text(POS_TEXT, reply_markup=choice_event_menu)
    return ConversationState.SELECT_EVENT_SERVICE if (step == TGMenu.SERVICE) and admin_status else ConversationState.SELECT_EVENT


@manage_menu(level=2)
def show_event_service_menu(query, context):
    """ Build and show event service menu """
    user = query.message.from_user
    admin_status = context.user_data['connector'].get_user_admin(user['id'])
    if not admin_status:
        return show_main_menu(query, context, custom_text=TGText.ERROR)

    # initialize
    event = context.user_data.get('events', {}).get(query.message.text)
    context.user_data['selected_event'] = event
    # build service actions menu
    rawreport = context.user_data['connector'].get_visitors_info(event['activity_id'])    
    if rawreport:
        service_menu = build_keyboard([
            [TGMenu.DOWNLOAD_REGISTRED], 
            [TGMenu.SEND_NOTIFY],       # TODO remove this if event is in past
            [TGMenu.BACK]], 
            resize_keyboard=True)
        context.user_data['report'] = rawreport
        # query.message.reply_text(, reply_markup=None, parse_mode=ParseMode.MARKDOWN)
    else:
        # if no items - move back to choosing event
        query.message.reply_text(TGText.NO_REGISTRATIONS)
        return show_select_event_menu(query, context)
    query.message.reply_text(TGText.BASIC_MENU_REQUEST, reply_markup=service_menu)
    return ConversationState.SELECT_ACTION


@manage_menu(level=2)
def show_event_actions_menu(query, context):
    """ Build and show event user action menu """
    user = query.message.from_user
    menu = context.user_data['menu_tree']
    event = context.user_data.get('events', {}).get(query.message.text)
    context.user_data['selected_event'] = event
    if not event:
        return show_start_menu(query, context, custom_text=TGText.ERROR)

    # show messages in depending on menu tree
    if menu[0] == TGMenu.ANNOUNCE:
        if event['info']:
            query.message.reply_text(event['info'], reply_markup=None, parse_mode=ParseMode.MARKDOWN)
        query.message.reply_text(TGText.FREE_PLACES % event.free_places, reply_markup=None, parse_mode=ParseMode.MARKDOWN)

    # NOTE there is just one action for users
    # that's why this method is skipping state and returns `handle_select_action_menu` directly
    context.user_data['question_state'] = event.isregistred(user['id'])
    return handle_select_action_menu(query, context, direct=TGMenu.SWITCH_REGISTER)
    # return ConversationState.SELECT_ACTION


@manage_menu(level=3)
def handle_select_action_menu(query, context, direct=None):     # NOTE `direct` may be removed in future
    """ Handle action choice and ask for confirmation """
    # initialize
    step = direct if direct else query.message.text
    question_state = context.user_data.pop('question_state', False)

    action = actions.get(step)      # get selected action callable and its description
    context.user_data['action'] = action
    actions_menu = build_keyboard([[TGMenu.ACCEPT, TGMenu.DECLINE]], resize_keyboard=True)
    # show action choosing menu
    query.message.reply_text(action.positive.question if question_state else action.negative.question, reply_markup=actions_menu)
    return ConversationState.CONFIRM_ACTION


def handle_confirmation(query, context):
    """ Build confirmation menu """
    text = query.message.text
    # admin_status = context.user_data['connector'].get_user_admin(user['id'])
    action = context.user_data.pop('action', None)
    # params = context.user_data.pop('action_params', {})

    if (text == TGMenu.ACCEPT) and action:
        succeed, answer_state = action.callback(query, context)
        if not succeed:
            return show_start_menu(query, context, custom_text=TGText.ERROR)
        query.message.reply_text(action.positive.answer if answer_state else action.negative.answer, parse_mode=ParseMode.MARKDOWN)
    else:
        query.message.reply_text(TGText.DEFAULT_CANCELLED, parse_mode=ParseMode.MARKDOWN)

    return show_select_event_menu(query, context)
    # return show_main_menu(query, context)


if __name__ == '__main__':
    # init bot updater
    updater = Updater(token=keyring.get_password('telegram', 'botuser'))
    dispatcher = updater.dispatcher
    # init handlers
    conversation_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.text, show_main_menu)],
        states={    # conversation states dictionary
            ConversationState.MAIN_MENU: [
                MessageHandler(Filters.regex(TGMenu.DEBUG), debugger),
                MessageHandler(Filters.regex(f'{TGMenu.ANNOUNCE}|{TGMenu.PERSONAL}|{TGMenu.SERVICE}'), show_select_event_menu),
                MessageHandler(Filters.regex(TGMenu.GOODBYE), show_start_menu),
                MessageHandler(Filters.text, partial(show_main_menu, custom_text=TGText.ERROR)),
            ],
            ConversationState.SELECT_EVENT: [
                MessageHandler(Filters.regex(TGMenu.BACK), partial(show_main_menu, custom_text=TGText.BASIC_REQUEST)),
                MessageHandler(Filters.text, show_event_actions_menu),      # --> SELECT_ACTION
            ],
            ConversationState.SELECT_EVENT_SERVICE: [
                MessageHandler(Filters.regex(TGMenu.BACK), partial(show_main_menu, custom_text=TGText.BASIC_REQUEST)),
                MessageHandler(Filters.text, show_event_service_menu),      # --> SELECT_ACTION
            ],
            ConversationState.SELECT_ACTION: [
                MessageHandler(Filters.regex(TGMenu.BACK), show_select_event_menu),
                MessageHandler(Filters.text, handle_select_action_menu),        # --> CONFIRM_ACTION
            ],
            ConversationState.CONFIRM_ACTION: [
                MessageHandler(Filters.text, handle_confirmation),
            ]
        },
        fallbacks=[MessageHandler(Filters.text, show_main_menu)]
    )
    dispatcher.add_handler(conversation_handler)

    # run bot
    updater.start_polling()
    updater.idle()
