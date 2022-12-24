import logging
import pathlib
import configparser
import keyring

from telegram.ext import Updater, ConversationHandler, MessageHandler, CallbackQueryHandler, CommandHandler
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
# init connector
connector = BotConnector(dbname=config['DATABASE']['name'],
                         username=config['DATABASE']['user'],
                         schema=config['DATABASE']['schema'],
                         host=config['DATABASE']['host'],
                         port=config['DATABASE']['port'])
# read dialogs configuration
text = DialogMessages('dialogs.cnf')
menu = MenuHandler(text, connector)


def debugger(update, context):
    """ For manual testing new features or development """
    print('DEBUGGER CALLBACK')
    # return menu.direct_switch(update, context, target=CallbackData.ERROR, errstate=ErrorState.UNAVAILABLE)


if __name__ == '__main__':
    # init bot updater
    updater = Updater(token=keyring.get_password('telegram', 'botuser'))
    dispatcher = updater.dispatcher
    # init handlers
    conversation_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', menu.start),
            MessageHandler(Filters.text, menu.start)
        ],
        states={    # conversation states dictionary
            ConversationState.FIRST_MET: [
                MessageHandler(Filters.text, menu.first_met)
            ],

            ConversationState.MENU: [
                CallbackQueryHandler(debugger, pattern='DEBUG'),
                CallbackQueryHandler(menu.main, pattern=rf'^{CallbackData.MAIN}'),
                CallbackQueryHandler(menu.available_activities, pattern=rf'^{CallbackData.ANNOUNCE}|{CallbackData.MYBOOKING}'),
                CallbackQueryHandler(menu.service_activities, pattern=rf'^{CallbackData.SERVICE}'),
                CallbackQueryHandler(menu.activity_info, pattern=rf'^{CallbackData.MORE}'),
                CallbackQueryHandler(menu.showmap, pattern=rf'^{CallbackData.SHOWMAP}'),
                CallbackQueryHandler(menu.showticket, pattern=rf'^{CallbackData.SHOWTICKET}'),
                CallbackQueryHandler(menu.book, pattern=rf'^{CallbackData.BOOK}'),
                CallbackQueryHandler(menu.book_confirm, pattern=rf'^{CallbackData.BOOK_CONFIRM}'),
                CallbackQueryHandler(menu.book_result, pattern=rf'^{CallbackData.BOOK_ACCEPT}'),
                CallbackQueryHandler(partial(menu.direct_switch, target=CallbackData.GOODBYE), pattern=rf'^{CallbackData.GOODBYE}'),
                MessageHandler(Filters.text, menu.message)
            ],

            ConversationHandler.TIMEOUT: [
                MessageHandler(Filters.all, partial(menu.direct_switch, target=CallbackData.ERROR, errstate=ErrorState.TIMEOUT)),
                CallbackQueryHandler(partial(menu.direct_switch, target=CallbackData.ERROR, errstate=ErrorState.TIMEOUT)),
            ]
        },
        fallbacks=[],
        conversation_timeout=int(config['BOT']['timeout']),
    )
    dispatcher.add_handler(conversation_handler)
    dispatcher.add_handler(CallbackQueryHandler(menu.admin_confirm, pattern=rf'^{CallbackData.BOOK_CONFIRM_ADMIN}'))
#     dispatcher.add_handler(CommandHandler('checkticket', menu.check_ticket))

    # run bot
    updater.start_polling()
    updater.idle()
