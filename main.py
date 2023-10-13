import requests
import random
import time
import telebot
from telebot import types
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import logging
import os
from dotenv import load_dotenv
from src.database import add_word_to_db, get_all_words_from_db, remove_word_from_db, find_word_in_db
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
    chat_id = message.chat.id
    user_id = message.from_user.id
    words = get_all_words_from_db(user_id)
    
    if words:
        markup = types.InlineKeyboardMarkup()
        
        # Show words for the current page
        for word in words[(page-1)*5:page*5]:
            btn = types.InlineKeyboardButton(word, callback_data=f"define_{word}")
            markup.add(btn)
        
        # Add navigation buttons
        if page > 1:
            markup.add(types.InlineKeyboardButton("<< Prev", callback_data=f"page_{page-1}"))
        if len(words) > page * 5:
            markup.add(types.InlineKeyboardButton("Next >>", callback_data=f"page_{page+1}"))
        
        bot.send_message(chat_id, "Your dictionary:", reply_markup=markup)
    else:
        bot.send_message(chat_id, "Your dictionary is empty.")

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.message:
        if call.data.startswith("define_"):
            word_to_define = call.data[7:]
            definition = get_definition(word_to_define)
            bot.send_message(call.message.chat.id, definition)
        elif call.data.startswith("page_"):
            page = int(call.data[5:])
            show_all_words(call.message, page)

# Handler for processing user input
@bot.message_handler(func=lambda message: True)
def process_user_input(message):
    chat_id = message.chat.id
    text = message.text.lower()

    # Check if the user wants to add the word to the local dictionary
    if text.startswith('/add'):
        word = text.split(' ', 1)[1]
        local_dictionary[word] = None
        send_message_in_parts(chat_id, f"The word '{word}' has been added to your local dictionary.")
    
    # Check if the user wants to receive a translation
    elif text.startswith('/translate'):
        word = text.split(' ', 1)[1]
        translation = get_translation(word)
        if translation:
            send_message_in_parts(chat_id, f"The translation of '{word}' in Russian is '{translation}'.")
        else:
            send_message_in_parts(chat_id, f"Translation not found for the word '{word}'.")
    
    # Check if the user wants to remove a word from the local dictionary
    elif text.startswith('/remove'):
        word = text.split(' ', 1)[1]
        if word in local_dictionary:
            del local_dictionary[word]
            send_message_in_parts(chat_id, f"The word '{word}' has been removed from your local dictionary.")
        else:
            send_message_in_parts(chat_id, f"The word '{word}' is not present in your local dictionary.")
    
    # Check if the user wants a random word reminder
    elif text.startswith('/reminder'):
        random_word = random.choice(list(local_dictionary.keys()))
        local_dictionary[random_word] = time.time()
        send_message_in_parts(chat_id, f"Here's a random word from your local dictionary: {random_word}")
    
    # Check if the user wants the definition of a word
    else:
        definition = get_definition(text)
        send_message_in_parts(chat_id, definition, text)
        # Create inline keyboard
        markup = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton("Add to Dictionary", callback_data=f"add_{text}")
        markup.add(btn)

        # Send message with inline keyboard
        bot.send_message(chat_id, "Would you like to add this word to your dictionary?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.message:
        if call.data.startswith("add_"):
            word_to_add = call.data[4:]
            user_id = call.message.chat.id  # Get user_id from message
            add_word_to_db(word_to_add, user_id)  # Pass both arguments to function
            bot.answer_callback_query(call.id, "Word added to your dictionary.")





# Function to send a message in parts to handle long messages
def send_message_in_parts(chat_id, text, word,  max_length=3800):

# Add the YouGlish link to the text
    text += f"\n\nYou can listen to the pronunciation of the word here: https://youglish.com/pronounce/{word}/english"
    text = format_text(text)

    if len(text) <= max_length:
        bot.send_message(chat_id, text, parse_mode='Markdown')
    else:
        parts = [text[i:i + max_length] for i in range(0, len(text), max_length)]
        for part in parts:
            bot.send_message(chat_id, part, parse_mode='Markdown')

# Start the bot
if __name__ == "__main__":
    # Local dictionary to store user-added words
    local_dictionary = {}
    
    logging.info("Starting the bot...")
    bot.polling()