import requests
import random
import time
import telebot
from telebot import types
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import logging
import os
from src.database import add_word_to_db, get_words_from_db, get_word_count, delete_word_from_db
from src.utilities import log_request, get_definition, format_text, get_translation

# Init Database
import src.db_init

# Load environment variables from .env file
load_dotenv()

# Telegram bot token
TOKEN = os.getenv("TOKEN")

# Merriam-Webster API key
MERRIAM_WEBSTER_API_KEY = os.getenv("MERRIAM_WEBSTER_API_KEY")

# Initialize the Telegram bot
bot = telebot.TeleBot(TOKEN, num_threads=10)

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

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
    - /translate [word]: Get the translation of a word to Russian
    - /remove [word]: Remove a word from your local dictionary
    - /reminder: Get a random word reminder from your local dictionary
    - /help: Show this help message
    """
    bot.reply_to(message, help_message)

@bot.message_handler(commands=['showwords'])
def show_all_words(message, page=1):
    user_id = message.from_user.id
    limit = 5
    offset = (page - 1) * limit
    words = get_words_from_db(user_id, limit, offset)
    total_words = get_word_count(user_id)
    
    if words:
        markup = types.InlineKeyboardMarkup()
        logging.debug(f"Fetched words: {words}")

        # Show words for the current page
        for word in words:
            btn = types.InlineKeyboardButton(word, callback_data=f"define_{word}")
            markup.add(btn)
        
        # Add navigation buttons
        if page > 1:
            prev_callback_data = f"page_{page-1}"
            markup.add(types.InlineKeyboardButton("<< Prev", callback_data=prev_callback_data))
            logging.debug(f"Added Prev button with callback_data: {prev_callback_data}")
        
        if total_words > page * limit:
            next_callback_data = f"page_{page+1}"
            markup.add(types.InlineKeyboardButton("Next >>", callback_data=next_callback_data))
            logging.debug(f"Added Next button with callback_data: {next_callback_data}")
        
        bot.send_message(message.chat.id, "Your dictionary:", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Your dictionary is empty.")


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.message:
        if call.data.startswith("define_"):
            word_to_define = call.data[7:]
            definition = get_definition(word_to_define)

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Dictionary", callback_data="showwords"))
            markup.add(types.InlineKeyboardButton("Delete Word", callback_data=f"delete_{word_to_define}"))
            send_message_in_parts(call.message.chat.id, definition, word_to_define, markup)

        elif call.data.startswith("delete_"):
            word_to_delete = call.data[7:]
            user_id = call.message.chat.id
            delete_word_from_db(word_to_delete, user_id)
            bot.answer_callback_query(call.id, "Word deleted from your dictionary.")
        
        elif call.data.startswith("add_"):
            word_to_add = call.data[4:]
            user_id = call.message.chat.id
            add_word_to_db(word_to_add, user_id)
            bot.answer_callback_query(call.id, "Word added to your dictionary.")

        elif call.data == "showwords":
            user_id = call.message.chat.id
            show_all_words(call.message)

        elif call.data.startswith("page_"):
            page = int(call.data.split("_")[1])
            logging.debug(f"Handling page callback: {page}")
            show_all_words(call.message, page)


# Handler for processing user input
@bot.message_handler(func=lambda message: True)
def process_user_input(message):
    chat_id = message.chat.id
    text = message.text.lower()

    if text.startswith('/translate'):
        word = text.split(' ', 1)[1]
        translation = get_translation(word)
        if translation:
            send_message_in_parts(chat_id, f"The translation of '{word}' in Russian is '{translation}'.", word)
        else:
            send_message_in_parts(chat_id, f"Translation not found for the word '{word}'.", word)
    
    elif text.startswith('/reminder'):
        random_word = random.choice(list(local_dictionary.keys()))
        local_dictionary[random_word] = time.time()
        send_message_in_parts(chat_id, f"Here's a random word from your local dictionary: {random_word}", random_word)
    
    else:
        definition = get_definition(text)
        send_message_in_parts(chat_id, definition, text)
        markup = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton("Add to Dictionary", callback_data=f"add_{text}")
        markup.add(btn)
        bot.send_message(chat_id, "Would you like to add this word to your dictionary?", reply_markup=markup)

# Function to send a message in parts to handle long messages
def send_message_in_parts(chat_id, text, word, markup=None, max_length=3800):
    text += f"\n\nYou can listen to the pronunciation of the word here: https://youglish.com/pronounce/{word}/english"
    text = format_text(text)

    parts = [text[i:i + max_length] for i in range(0, len(text), max_length)]
    for part in parts[:-1]:
        bot.send_message(chat_id, part, parse_mode='Markdown')
    bot.send_message(chat_id, parts[-1], parse_mode='Markdown', reply_markup=markup)

# Start the bot
if __name__ == "__main__":
    local_dictionary = {}
    logging.info("Starting the bot...")
    bot.polling()
