import logging
import pathlib
import configparser
import keyring

from telegram import ParseMode
from telegram.ext import Updater, ConversationHandler, MessageHandler, CallbackQueryHandler, InlineQueryHandler
from telegram.ext.filters import Filters

from menu import MenuHandler
from states import ErrorState, CallbackData, ConversationState, DialogMessages
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

# read dialogs configuration
text = DialogMessages('dialogs.cnf')
menu = MenuHandler(text)


def debugger(update, context):
    """ For manual testing new features or development """
    print('DEBUGGER CALLBACK')
    return ConversationState.MENU


def incorrect_input(update, context):
    update.message.delete()
    return ConversationState.MENU


def start(update, context):
    """ Initialize conversation """
    update.message.delete()
    user = update.message.from_user
    context.user_data['uid'] = user['id']
    # init connector
    connector = BotConnector(dbname=config['DATABASE']['name'],
                             username=config['DATABASE']['user'],
                             schema=config['DATABASE']['schema'],
                             host=config['DATABASE']['host'],
                             port=config['DATABASE']['port'])
    context.user_data['connector'] = connector
    # request user data
    if not (specname := connector.get_user_field(user['id'], field='specname')):
        context.user_data['last_message'] = update.message.reply_text(text['MESSAGE', 'FIRST_MET'], reply_markup=None, parse_mode=ParseMode.MARKDOWN)   # TODO Hide keyboard ?
        return ConversationState.FIRST_MET
    
    context.user_data['specname'] = specname
    context.user_data['cvstate'] = 1      # user exists state
    return menu.main(update, context)


def first_met(update, context):
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
    context.user_data['connector'].set_user(user['id'], **data)
    context.user_data['specname'] = specname
    context.user_data['cvstate'] = 0      # new user state
    update.message.delete()
    return menu.main(update, context)


if __name__ == '__main__':
    # init bot updater
    updater = Updater(token=keyring.get_password('telegram', 'botuser'))
    dispatcher = updater.dispatcher
    # init handlers
    conversation_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.text, start)],
        states={    # conversation states dictionary
            ConversationState.FIRST_MET: [
                MessageHandler(Filters.text, first_met)
            ],

            ConversationState.MENU: [
                # CallbackQueryHandler(debugger, pattern='DEBUG'),
                CallbackQueryHandler(menu.main, pattern=rf'^{CallbackData.MAIN}'),
                CallbackQueryHandler(menu.available_activities, pattern=rf'^{CallbackData.ANNOUNCE}|{CallbackData.MYBOOKING}'),
                CallbackQueryHandler(menu.service_activities, pattern=rf'^{CallbackData.SERVICE}'),
                CallbackQueryHandler(menu.activity_info, pattern=rf'^{CallbackData.MORE}'),
                CallbackQueryHandler(menu.showmap, pattern=rf'^{CallbackData.SHOWMAP}'),
                CallbackQueryHandler(menu.book, pattern=rf'^{CallbackData.BOOK}'),
                CallbackQueryHandler(menu.book_confirm, pattern=rf'^{CallbackData.BOOK_CONFIRM}'),
                CallbackQueryHandler(menu.book_result, pattern=rf'^{CallbackData.BOOK_ACCEPT}'),
                CallbackQueryHandler(menu.goodbye, pattern=rf'^{CallbackData.GOODBYE}'),
                # CallbackQueryHandler(menu.action, pattern='action'),  # deprecated
            ],

            ConversationHandler.TIMEOUT: [
                MessageHandler(Filters.all, partial(menu.raise_error, state=ErrorState.TIMEOUT)),
                CallbackQueryHandler(partial(menu.raise_error, state=ErrorState.TIMEOUT)),
            ]
        },
        fallbacks=[MessageHandler(Filters.all, incorrect_input)],
        conversation_timeout=int(config['BOT']['timeout']),
    )
    dispatcher.add_handler(conversation_handler)

    # run bot
    updater.start_polling()
    updater.idle()
