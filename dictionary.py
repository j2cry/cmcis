LINK = 'https://t.me/land_of_untold_stories'


class TGMenu:
    """ Button titles """
    # common
    HELLO = 'Привет!'
    BACK = 'Назад'
    ACCEPT = 'Да'
    DECLINE = 'Нет'
    # main menu
    ANNOUNCE = 'Доступные сеансы'
    PERSONAL = 'Мои записи'
    SERVICE = 'Служебная информация'
    GOODBYE = 'До свидания'
    DEBUG = 'debug'
    # actions menu
    SWITCH_REGISTER = 'Зарегистрироваться'
    DOWNLOAD_REGISTRED = 'Список зарегистрированных пользователей'
    SEND_NOTIFY = 'Разослать напоминания'


class TGText:
    """ Bot answers """
    WELCOME = 'Привет! Меня зовут Harpy. Выберите, чем я могу вам помочь.'
    WELCOME_ADMIN = 'Привет, Гуру'
    BASIC_REQUEST = 'Выберите, чем я могу вам помочь.'
    BASIC_MENU_REQUEST = 'Выберите действие'
    FAREWELL = 'До встречи!'
    PUBLIC_EVENTS = 'Вот доступные сеансы, на которые вы еще не зарегистрированы. Сеансы, на которые вы уже зарегистрированы, можно найти в разделе "Мои записи"'
    ZERO_PUBLIC_EVENTS = f'На данный момент новых мероприятий не анонсировано или на них закончились места. ' \
                         f'Подписывайтесь и следите за новостями в [основном канале]({LINK}). ' \
                         f'По всем вопросам вы можете написать [Геннадию](tg://user?id=1474200050).'
    PERSONAL_EVENTS = 'Вот сеансы, на которые вы записаны'
    ZERO_PERSONAL_EVENTS = 'У вас еще нет записей на сеансы'
    ADMIN_EVENTS = 'Cеансы'
    ZERO_ADMIN_EVENTS = 'Нет сеансов для админстрирования'

    FREE_PLACES = 'На этот сеанс осталось %s мест'
    ERROR = 'Кажется, что-то пошло не так. Попробуйте еще раз.'
    
    # TGActions
    DEFAULT_CONFIRM_QUESTION = 'Внести изменения?'
    DEFAULT_ACCEPTED = 'Изменения внесены'
    DEFAULT_CANCELLED = 'Изменения не внесены'

    REGISTRED_POSITIVE = 'Вы уже записаны на сеанс, хотите отменить запись?'
    REGISTRED_NEGATIVE = 'Вы еще не записаны, хотите записаться?'
    REGISTER_ACCEPTED = 'Вы записаны на сеанс'
    REGISTER_CANCELLED = 'Вы отменили запись на сеанс'

    REGISTRATIONS_REQUEST = 'Скачать информацию о записях?'
    REGISTRATIONS_DOWNLOAD = 'Файл отправлен.'
    NO_REGISTRATIONS = 'На этот сеанс еще никто не зарегистрирован.'

    NOTIFY_REQUEST = 'Отправить напоминания?'
    NOTIFY_SENT = 'Напоминания отправлены.'
    NOTIFICATION = 'Привет! Вы записаны на мероприятие %s, которое начнется %s в %s по адресу %s.\n'\
                   'Ждем вас на мероприятии!'
