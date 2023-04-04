import requests


def sendMessage(chat_id: str, data: str, token: str) -> None:
    url = f'https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={data}'
    requests.get(url)
