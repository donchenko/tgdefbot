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
from src.utilities import log_request, get_definition, format_text
from src.audio_handler import get_audio_file

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
logging.basicConfig(level=logging.INFO)

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
def show_all_words(message, page=1, user_id=None):
    if user_id is None:
        user_id = message.from_user.id
    limit = 5
    offset = (page - 1) * limit
    words = get_words_from_db(user_id, limit, offset, sort=True)
    total_words = get_word_count(user_id)
    
    logging.info(f"show_all_words called with page={page}, user_id={user_id}, limit={limit}, offset={offset}")
    
    if words:
        markup = types.InlineKeyboardMarkup()
        logging.info(f"Fetched words for page {page}: {words}")

        # Show words for the current page
        for word in words:
            btn = types.InlineKeyboardButton(word, callback_data=f"define_{word}_{user_id}")
            markup.add(btn)

        # Pagination buttons
        if page > 1:
            prev_callback_data = f"page_{page-1}_{user_id}"
            markup.add(types.InlineKeyboardButton("<< Prev", callback_data=prev_callback_data))
            logging.info(f"Added Prev button with callback_data: {prev_callback_data}")
        
        if total_words > page * limit:
            next_callback_data = f"page_{page+1}_{user_id}"
            markup.add(types.InlineKeyboardButton("Next >>", callback_data=next_callback_data))
            logging.info(f"Added Next button with callback_data: {next_callback_data}")

        bot.send_message(message.chat.id, "Your words:", reply_markup=markup)
    else:
        logging.info(f"No words found for user {user_id} on page {page}")
        bot.send_message(message.chat.id, "Your dictionary is empty.")

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.message:
        logging.info(f"callback_inline called with data: {call.data}")
        data_parts = call.data.split("_")
        action = data_parts[0]
        user_id = int(data_parts[-1])  # Get the last part as user_id
        
        logging.info(f"Action: {action}, User ID: {user_id}")
        
        if action == "define":
            word_to_define = "_".join(data_parts[1:-1])  # Join all parts except the action and user_id
            definition = get_definition(word_to_define)
            logging.info(f"Definition for {word_to_define}: {definition}")

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Dictionary", callback_data=f"showwords_{user_id}"))
            markup.add(types.InlineKeyboardButton("Delete Word", callback_data=f"delete_{word_to_define}_{user_id}"))
            
            # Extract audio link from definition
            audio_link = definition.split("Audio: ")[-1].split("\n")[0]
            audio_path = get_audio_file(word_to_define, audio_link)
            
            send_message_in_parts(call.message.chat.id, definition, word_to_define, audio_path, markup)
            bot.answer_callback_query(call.id)  # Add this line to handle the callback

        elif action == "delete":
            word_to_delete = "_".join(data_parts[1:-1])  # Join all parts except the action and user_id
            delete_word_from_db(word_to_delete, user_id)
            bot.answer_callback_query(call.id, "Word deleted from your dictionary.")
            logging.info(f"Deleted word: {word_to_delete}")

        elif action == "add":
            word_to_add = "_".join(data_parts[1:-1])  # Join all parts except the action and user_id
            add_word_to_db(word_to_add, user_id)
            bot.answer_callback_query(call.id, "Word added to your dictionary.")
            logging.info(f"Added word: {word_to_add}")
            
            # Adding "Dictionary" button after word addition
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Dictionary", callback_data=f"showwords_{user_id}"))
            bot.send_message(call.message.chat.id, "Word added to your dictionary.", reply_markup=markup)

        elif action == "showwords":
            logging.info(f"Showing words for user: {user_id}")
            show_all_words(call.message, page=1, user_id=user_id)
            bot.answer_callback_query(call.id)

        elif action == "page":
            page = int(data_parts[1])
            logging.info(f"Handling page callback: {page}")
            show_all_words(call.message, page, user_id=user_id)
            bot.answer_callback_query(call.id)

# Handler for processing user input
@bot.message_handler(func=lambda message: True)
def process_user_input(message):
    chat_id = message.chat.id
    text = message.text.lower()

    logging.info(f"process_user_input called with text: {text}")

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
        btn = types.InlineKeyboardButton("Add to Dictionary", callback_data=f"add_{text}_{message.from_user.id}")
        markup.add(btn)
        bot.send_message(chat_id, "Would you like to add this word to your dictionary?", reply_markup=markup)

# Function to send a message in parts to handle long messages
def send_message_in_parts(chat_id, text, word, audio_path=None, markup=None, max_length=3800):
    text += f"\n\nYou can listen to the pronunciation of the word here: https://youglish.com/pronounce/{word}/english"
    text = format_text(text)

    parts = [text[i:i + max_length] for i in range(0, len(text), max_length)]
    for part in parts[:-1]:
        bot.send_message(chat_id, part, parse_mode='Markdown')
    if audio_path:
        bot.send_audio(chat_id, open(audio_path, 'rb'), caption=parts[-1], parse_mode='Markdown', reply_markup=markup)
    else:
        bot.send_message(chat_id, parts[-1], parse_mode='Markdown', reply_markup=markup)

# Start the bot
if __name__ == "__main__":
    local_dictionary = {}
    logging.info("Starting the bot...")
    bot.polling()
