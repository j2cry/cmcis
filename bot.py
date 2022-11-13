import logging
import pathlib
import configparser
import keyring
from telegram import ParseMode
from telegram.ext import Updater, ConversationHandler, MessageHandler, CallbackQueryHandler
from telegram.ext.filters import Filters
from aux import ConversationState, actions, build_menu
from dictionary import  TGText, TGMenu
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


def debugger(query, context):
    """ For manual testing new features or development """
    query.message.reply_text('DEBUG ACTION')
    return ConversationState.MAIN_MENU


def show_start_menu(query, context, custom_text=None):
    """ Drop conversation and show start menu """
    query.message.reply_text(custom_text if custom_text else TGText.FAREWELL, reply_markup=build_menu([[TGMenu.HELLO]], resize_keyboard=True))
    return ConversationHandler.END


def show_main_menu(query, context, custom_text=None):
    """ Initialize conversation and show main menu """
    # initialize
    user = query.message.from_user
    context.user_data.clear()
    context.user_data['section'] = None    # main menu section
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
    main_menu = build_menu([
        [TGMenu.ANNOUNCE, TGMenu.PERSONAL],
        [TGMenu.SERVICE] if admin_status else [],
        [TGMenu.DEBUG] if admin_status else [],     # NOTE DEBUG FEATURE
        [TGMenu.GOODBYE]
    ], resize_keyboard=True)

    # query.message.reply_text(backward if backward else TGText.WELCOME.replace('$name', user['first_name']), reply_markup=main_menu)   # personalized welcome message
    query.message.reply_text(custom_text if custom_text else TGText.WELCOME, reply_markup=main_menu, parse_mode=ParseMode.MARKDOWN)   # welcome message
    return ConversationState.MAIN_MENU


def handle_main_menu(query, context):
    """ Handle main menu choice and prepare context for the next step """
    # initialize
    step = query.message.text
    # route conversation
    if step in (TGMenu.ANNOUNCE, TGMenu.PERSONAL, TGMenu.SERVICE):
        pass
    elif step == TGMenu.GOODBYE:
        return show_start_menu(query, context)
    elif step == TGMenu.DEBUG:
        # TODO logger code
        return debugger(query, context)
    else:   # any other message
        # TODO logger code
        return show_main_menu(query, context)
    # prepare and show next menu
    context.user_data['section'] = step      # remember menu section
    return show_choice_event_menu(query, context)


def show_choice_event_menu(query, context, direct=None):
    """ Build and show events list menu """
    # initialize
    user = query.message.from_user
    step = direct if direct else query.message.text
    admin_status = context.user_data['connector'].get_user_admin(user['id'])

    if step == TGMenu.ANNOUNCE:
        context.user_data['events_text'] = TGText.PUBLIC_EVENTS
        context.user_data['no_events_text'] = TGText.ZERO_PUBLIC_EVENTS
    elif step == TGMenu.PERSONAL:
        context.user_data['events_text'] = TGText.PERSONAL_EVENTS
        context.user_data['no_events_text'] = TGText.ZERO_PERSONAL_EVENTS
    elif (step == TGMenu.SERVICE) and admin_status:
        context.user_data['events_text'] = f'{TGMenu.SERVICE}: {TGText.ADMIN_EVENTS.lower()}'
        context.user_data['no_events_text'] = TGText.ZERO_ADMIN_EVENTS

    # request events and check its length
    events = context.user_data['connector'].get_events(step, uid=user['id'])
    if not len(events):        # back to parent menu
        # TODO logger code
        return show_main_menu(query, context, custom_text=context.user_data['no_events_text'])

    # collect events for context TODO: display free places on keyboard
    ev_names = [ev.formatted_title(multirow=True) for ev in events]     # collect button names    BUG NOTE: NAMES COLLISION !!!
    context.user_data['events'] = dict(zip(ev_names, events))       # update user context
    # build events menu
    menu_items = [*list(map(lambda x: [x], ev_names)), [TGMenu.BACK]]
    choice_event_menu = build_menu(menu_items, resize_keyboard=True)
    # route conversation to the next step: show event choosing menu
    query.message.reply_text(context.user_data['events_text'], reply_markup=choice_event_menu)
    return ConversationState.SELECT_EVENT


def handle_choice_event_menu(query, context):
    """ Handle event choice menu and prepare context for the next step """
    # initialize
    user = query.message.from_user
    step = query.message.text
    section = context.user_data.get('section')
    admin_status = context.user_data['connector'].get_user_admin(user['id'])

    # on back button pressed
    if step == TGMenu.BACK:
        return show_main_menu(query, context, custom_text=TGText.BASIC_REQUEST)
    # get selected event
    event = context.user_data.get('events', {}).get(step)
    # show messages in depending on menu section
    if (section == TGMenu.ANNOUNCE):        
        if event['info']:
            query.message.reply_text(event['info'], reply_markup=None, parse_mode=ParseMode.MARKDOWN)
        query.message.reply_text(TGText.FREE_PLACES % event.free_places, reply_markup=None, parse_mode=ParseMode.MARKDOWN)
    # handling: prepare conversation context
    context.user_data['selected_event'] = event
    # route conversation
    if admin_status and (section == TGMenu.SERVICE):
        context.user_data['EVENTS_TEXT'] = TGText.BASIC_MENU_REQUEST
        return show_event_service_menu(query, context)

    return show_event_actions_menu(query, context)


def show_event_service_menu(query, context, direct=None):
    """ Build and show event service menu """
    # initialize
    # step = context.user_data.get('step')
    step = direct if direct else query.message.text
    event = context.user_data.get('events', {}).get(step)
    # build service actions menu
    rawreport = context.user_data['connector'].get_visitors_info(event['activity_id'])    
    if rawreport:
        service_menu = build_menu([[TGMenu.DOWNLOAD_REGISTRED], [TGMenu.SEND_NOTIFY], [TGMenu.BACK]], resize_keyboard=True)
        context.user_data['report'] = rawreport
        # query.message.reply_text(, reply_markup=None, parse_mode=ParseMode.MARKDOWN)
    else:
        # if no items - move back to choosing event
        query.message.reply_text(TGText.NO_REGISTRATIONS)
        return show_choice_event_menu(query, context, direct=context.user_data['section'])
    query.message.reply_text(context.user_data['EVENTS_TEXT'], reply_markup=service_menu)
    return ConversationState.SELECT_ACTION


def show_event_actions_menu(query, context):
    """ Build and show event user action menu """
    # NOTE there is just one action for users
    # that's why this method is skipping `handle_choice_action_menu`
    user = query.message.from_user
    if not (event := context.user_data.get('selected_event')):
        return show_start_menu(query, context, custom_text=TGText.ERROR)
    
    context.user_data['question_state'] = event.isregistred(user['id'])
    return handle_choice_action_menu(query, context, direct=TGMenu.SWITCH_REGISTER)
    # return ConversationState.SELECT_ACTION


def handle_choice_action_menu(query, context, direct=None):
    """ Handle action choice and ask for confirmation 
    :param direct - process direct command
    """
    # initialize
    step = direct if direct else query.message.text
    section = context.user_data['section']
    question_state = context.user_data.pop('question_state', False)

    if step == TGMenu.BACK:
        return show_choice_event_menu(query, context, direct=section)

    action = actions.get(step)      # get selected action callable and its description
    context.user_data['action'] = action
    actions_menu = build_menu([[TGMenu.ACCEPT, TGMenu.DECLINE]], resize_keyboard=True)
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

    return show_choice_event_menu(query, context, direct=context.user_data['section'])
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
                # CallbackQueryHandler(announce, pattern=TGMenu.ANNOUNCE),
                # CallbackQueryHandler(announce, pattern=TGMenu.),
                MessageHandler(Filters.text, handle_main_menu),
            ],
            ConversationState.SELECT_EVENT: [
                MessageHandler(Filters.text, handle_choice_event_menu),
            ],
            ConversationState.SELECT_ACTION: [
                MessageHandler(Filters.text, handle_choice_action_menu),
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
