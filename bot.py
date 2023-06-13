import requests
import json
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor

bot = Bot(token='5878027549:AAFycCgVZmNC9zZLrFGZYp4ZmmvafVgZL6w')
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    await message.reply("Hello! I'm a bot for learning English. Send me a word and I'll give you its definition.")

@dp.message_handler()
async def echo_message(msg: types.Message):
    word = msg.text
    response = requests.get(f'https://dictionaryapi.com/api/v3/references/learners/json/{word}?key=33f93937-0d40-43f0-92cf-791974312d6d')
    data = response.json()[0]

    word = data['hwi']['hw']
    fl = data['fl']
    shortdef = ', '.join(data['shortdef'])
    ins = ', '.join([i['if'] for i in data['ins']])
    defs = '\n'.join([d['dt'][0][1] for d in data['def'][0]['sseq'][0]])

    message = f"Word: {word}\nPart of Speech: {fl}\nShort Definitions: {shortdef}\nOther Forms: {ins}\nDetailed Definitions:\n{defs}"
    await bot.send_message(msg.from_user.id, message)

if __name__ == '__main__':
    executor.start_polling(dp)
