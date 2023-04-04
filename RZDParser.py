import src
import telegramSender
from config import origin, destination, date, chat_id, token

data = src.parseTickets(src.getTickets(origin, destination, date))
telegramSender.sendMessage(chat_id, data, token)