import os
import time
import requests
import logging
import telegram
from http import HTTPStatus
from dotenv import load_dotenv
load_dotenv()


class CustomException(Exception):
    """Yet Another Custom Exception."""

    def __init__(self, error: str):
        self.error = error


class TokenException(CustomException):
    """Yet Another Custom Exception."""

    pass


class SendingMessageException(CustomException):
    """Yet Another Custom Exception."""

    pass


class GetApiException(CustomException):
    """Yet Another Custom Exception."""

    pass


class StatusParcingException(CustomException):
    """Yet Another Custom Exception."""

    pass


PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Raises an exception if even one token is empty."""
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for token in tokens:
        if not token:
            logging.critical("Some tokens are empty")
            raise CustomException.TokenException("Some tokens are empty")


def send_message(bot, message):
    """Sends message to the user."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug("Message sended successfully")
    except telegram.TelegramError as error:
        logging.error("Troubles with sending a message")
        raise CustomException.SendingMessageException(error)


def get_api_answer(timestamp):
    """Return's Practicum API's answer as a Python dict."""
    try:
        url = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
        headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
        payload = {'from_date': f"{timestamp}"}
        homework_statuses = requests.get(url, headers=headers, params=payload)
        match homework_statuses.status_code:  # flake8: noqa
            case HTTPStatus.OK:
                return homework_statuses.json()
            case _:
                error = "Troubles with getting to the Practicum API"
                raise CustomException.GetApiException(error)
    except requests.RequestException as error:
        raise CustomException.GetApiException(error)


def check_response(response):
    """Raises an Exception if response isn't correct."""
    try:
        match response:
            case response as r if not isinstance(r, dict):
                raise TypeError
            case response as r if not isinstance(r.get("current_date"), int):
                raise TypeError
            case response as r if not isinstance(r.get("homeworks"), list):
                raise TypeError
            case response as r if not isinstance(r.get("homeworks")[0], dict):
                raise TypeError
    except TypeError as error:
        raise TypeError(error)


def parse_status(homework):
    """Parses thestatus and other info of the homework."""
    homework_name = homework.get("homework_name")
    verdict_status = homework.get("status")
    if homework.get("homework_name") is None:
        raise CustomException.StatusParcingException()
    if homework.get("status") is None:
        raise CustomException.StatusParcingException()
    if (homework.get("status") != "approved"
            and homework.get("status") != "reviewing"
            and homework.get("status") != "rejected"):
        raise CustomException.StatusParcingException()
    verdict = HOMEWORK_VERDICTS.get(verdict_status)

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            message = None
            for homework in response.get("homeworks"):
                message = parse_status(homework)
            if message:
                send_message(bot, message)
            timestamp = int(response.get("current_date", timestamp))
            logging.debug("No homework updates")

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        filename='program.log',
        format='%(asctime)s, %(levelname)s, %(message)s, %(lineno)s'
    )
    main()
