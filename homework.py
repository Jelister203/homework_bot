import os
import time
import requests
import logging
import telegram
import exceptions
from http import HTTPStatus
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

URL = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'

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
            raise exceptions.TokenException("Some tokens are empty")


def send_message(bot, message):
    """Sends message to the user."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug("Message sended successfully")
    except telegram.TelegramError as error:
        logging.error("Troubles with sending a message")
        raise exceptions.SendingMessageException(error)


def get_api_answer(timestamp):
    """Return's Practicum API's answer as a Python dict."""
    try:
        headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
        payload = {'from_date': f"{timestamp}"}
        homework_statuses = requests.get(URL, headers=headers, params=payload)
        """
        match homework_statuses.status_code:  # Raises flake8 E999 error.
            case HTTPStatus.OK:
                return homework_statuses.json()
            case _:
                error = "Troubles with getting to the Practicum API"
                raise CustomException.GetApiException(error)
        """
        if homework_statuses.status_code == HTTPStatus.OK:
            return homework_statuses.json()
        error = "Troubles with getting to the Practicum API"
        raise exceptions.GetApiException(error)

    except requests.RequestException as error:
        raise exceptions.GetApiException(error)


def check_response(response):
    """Raises an Exception if response isn't correct."""
    """
    match response:  # Raises flake8 error too.
        case response as r if not isinstance(r, dict):
            raise TypeError
        case response as r if not isinstance(r.get("current_date"), int):
            raise TypeError
        case response as r if not isinstance(r.get("homeworks"), list):
            raise TypeError
        case response as r if not isinstance(r.get("homeworks")[0], dict):
            raise TypeError
    """
    if not isinstance(response, dict):
        raise TypeError("Invalid response type.",
                        "Expected dict, got " + type(response))
    if not isinstance(response.get("current_date"), int):
        raise TypeError("Invalid current_date type.",
                        "Expected int, got "
                        + type(response.get("current_date")))
    if not isinstance(response.get("homeworks"), list):
        raise TypeError("Invalid homeworks type.",
                        "Expected list, got "
                        + type(response.get("homeworks")))
    if not isinstance(response.get("homeworks")[0], dict):
        raise TypeError("Invalid current_date type.",
                        "Expected dict, got "
                        + type(response.get("homeworks")[0]))


def parse_status(homework):
    """Parses thestatus and other info of the homework."""
    homework_name = homework.get("homework_name")
    verdict_status = homework.get("status")
    if homework.get("homework_name") is None:
        raise exceptions.StatusParsingException()
    if homework.get("status") is None:
        raise exceptions.StatusParsingException()
    if (homework.get("status") != "approved"
            and homework.get("status") != "reviewing"
            and homework.get("status") != "rejected"):
        raise exceptions.StatusParsingException()
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
            timestamp = response.get("current_date", timestamp)
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
