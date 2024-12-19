import telebot
import os
import logging

TOKEN = os.getenv('TOKEN')
bot = telebot.TeleBot(TOKEN)

logging.basicConfig(level=logging.INFO)

def test_send_message():
    test_chat_id = '59666312'
    test_message = 'This is a test message.'

    try:
        bot.send_message(test_chat_id, test_message)
        logging.info('Test passed')
    except Exception as e:
        logging.error('Test failed:', e)

if __name__ == '__main__':
    test_send_message()
