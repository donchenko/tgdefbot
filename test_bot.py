import telebot
import os

TOKEN = os.getenv('TOKEN')
bot = telebot.TeleBot(TOKEN)

def test_send_message():
    # Замените 'test_chat_id' на ID тестового чата или пользователя
    test_chat_id = '59666312'
    test_message = 'This is a test message.'

    try:
        bot.send_message(test_chat_id, test_message)
        print('Test passed')
    except Exception as e:
        print('Test failed:', e)

if __name__ == '__main__':
    test_send_message()
