import os
import requests
import json
import random
import time
import telebot
from telebot import types
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram bot token
TOKEN = os.getenv("TOKEN")

# Merriam-Webster API key
MERRIAM_WEBSTER_API_KEY = os.getenv("MERRIAM_WEBSTER_API_KEY")

# Initialize the Telegram bot
bot = telebot.TeleBot(TOKEN)

# Handler for the "/start" command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Welcome to the English learning bot!")

# Handler for the "/help" command
@bot.message_handler(commands=['help'])
def send_help(message):
    help_message = """
Here are the available commands:
- /start: Start the bot
- /add [word]: Add a word to your local dictionary
- /remove [word]: Remove a word from your local dictionary
- /reminder: Get a random word reminder from your local dictionary
- /help: Show this help message
"""
    bot.reply_to(message, help_message)

# Handler for processing user input
@bot.message_handler(func=lambda message: True)
def process_user_input(message):
    chat_id = message.chat.id
    text = message.text.lower()

    # Check if the user wants to add the word to the local dictionary
    if text.startswith('/add'):
        word = text.split(' ', 1)[1]
        local_dictionary[word] = None
        bot.send_message(chat_id, f"The word '{word}' has been added to your local dictionary.")

    # Check if the user wants to remove a word from the local dictionary
    elif text.startswith('/remove'):
        word = text.split(' ', 1)[1]
        if word in local_dictionary:
            del local_dictionary[word]
            bot.send_message(chat_id, f"The word '{word}' has been removed from your local dictionary.")
        else:
            bot.send_message(chat_id, f"The word '{word}' is not present in your local dictionary.")

    # Check if the user wants a random word reminder
    elif text.startswith('/reminder'):
        random_word = random.choice(list(local_dictionary.keys()))
        local_dictionary[random_word] = time.time()
        bot.send_message(chat_id, f"Here's a random word from your local dictionary: {random_word}")

    # Check if the user wants the definition of a word
    else:
        definition = get_definition(text)
        bot.send_message(chat_id, definition)

def get_definition(word):
    url = f"https://dictionaryapi.com/api/v3/references/learners/json/{word}?key={MERRIAM_WEBSTER_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = json.loads(response.text)

        definitions = []
        for entry in data:
            # Extract headword information
            word = entry['hwi']['hw']
            prs = ', '.join([p['ipa'] for p in entry['hwi']['prs']])

            # Extract functional label
            fl = entry['fl']

            # Extract other forms of the word
            ins = ', '.join([i['if'] for i in entry.get('ins', [])])

            # Extract short definitions
            shortdef = ', '.join(entry['shortdef'])

            # Extract detailed definitions
            defs = []
            for sseq in entry['def'][0]['sseq']:
                for sense in sseq:
                    if isinstance(sense, list):
                        for item in sense:
                            if isinstance(item, dict) and 'dt' in item:
                                defs.append(item['dt'][0][1])
            defs = '\n'.join(defs)

            # Extract metadata
            id = entry['meta']['id']
            src = entry['meta']['src']

            definitions.append(f"Word: {word}\nPronunciation: {prs}\nPart of Speech: {fl}\nOther Forms: {ins}\nShort Definitions: {shortdef}\nDetailed Definitions:\n{defs}\nID: {id}\nSource: {src}")

        return '\n\n'.join(definitions)
    else:
        return "Error in API request."


# Start the bot
if __name__ == "__main__":

    # Local dictionary to store user-added words
    local_dictionary = {}

    bot.polling()
