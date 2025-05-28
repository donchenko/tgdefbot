import requests
import random
import time
import telebot
from telebot import types
from dotenv import load_dotenv
from bs4 import BeautifulSoup # Keep for now, though not explicitly used after refactor
import logging
import os
from typing import Tuple, Optional, List, Dict, Any, Union

# Assuming these are correctly imported and function as expected
from src.database import add_word_to_db, get_words_from_db, get_word_count, delete_word_from_db, \
    get_word_by_id # Added get_word_by_id for quiz stats
from src.utilities import log_request, get_definition, format_text
from src.audio_handler import get_audio_file
from commands.start import get_welcome_message
from src.quiz_handler import MIN_WORDS_FOR_QUIZ, generate_quiz_question, check_quiz_answer # For quiz

# Init Database (ensure this script is idempotent and safe to run)
import src.db_init 

# Load environment variables from .env file
load_dotenv()

# --- Constants ---
TOKEN = os.getenv("TOKEN")
# MERRIAM_WEBSTER_API_KEY is used in utilities.py, loaded via its own load_dotenv or passed if necessary.

# Callback Prefixes
CALLBACK_PREFIX_DEFINE = "define_"
CALLBACK_PREFIX_DELETE = "delete_"
CALLBACK_PREFIX_ADD = "add_"
CALLBACK_PREFIX_SHOWWORDS = "showwords_"
CALLBACK_PREFIX_PAGE = "page_"
CALLBACK_PREFIX_DICTIONARY = "showwords"
CALLBACK_PREFIX_QUIZ_ANSWER = "quizans_"
CALLBACK_PREFIX_NEXT_QUIZ = "quiznext_"

# --- Bot Initialization ---
# Ensure TOKEN is valid before initializing bot
if TOKEN is None:
    # Log this critical error and exit or raise an exception
    # For now, basic print and exit for critical setup failure
    print("CRITICAL: Telegram Bot TOKEN is not set. Exiting.")
    exit() # Or raise SystemExit / specific exception

bot = telebot.TeleBot(TOKEN, num_threads=10)

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- In-memory storage for current quiz data (for simplicity) ---
current_quiz_data: Dict[int, Dict[str, Any]] = {}
local_dictionary: Dict[str, float] = {} # For /reminder feature

# --- Command Handlers ---
@bot.message_handler(commands=['start'])
def send_welcome(message: types.Message) -> None:
    try:
        log_request(message) 
        welcome_text = get_welcome_message() 
        bot.reply_to(message, welcome_text)
        logger.info(f"Sent welcome message to user {message.from_user.id}")
    except telebot.apihelper.ApiException as e:
        logger.error(f"API Error in send_welcome for user {message.from_user.id}: {e}")
        bot.reply_to(message, "Sorry, there was an error processing your /start command.")
    except Exception as e:
        logger.error(f"Unexpected error in send_welcome for user {message.from_user.id}: {e}", exc_info=True)
        bot.reply_to(message, "An unexpected error occurred. Please try again later.")

@bot.message_handler(commands=['help'])
def send_help(message: types.Message) -> None:
    try:
        log_request(message) 
        help_text = """
*Welcome to the LexiLearn Bot!* Here's how I can help you expand your vocabulary:

*Getting Started & Help:*
  `/start` - Display the welcome message.
  `/help` - Show this help message with all available commands.

*Managing Your Dictionary:*
  `/showwords` - View all words currently in your personal dictionary.
  `/add [word]` - Add a specific word to your dictionary. Example: `/add lexicon`
  `/remove [word]` - Remove a specific word. Example: `/remove lexicon`

*Learning & Practice:*
  `/quiz` - Start a quiz with words from your dictionary.
  
*Word Lookup:*
  Simply type any English word (e.g., "ubiquitous") to get its definition, pronunciation, and an option to add it to your dictionary.

*Experimental Features:*
  `/translate [word]` - Get an English-to-Russian translation.
  `/reminder` - Get a random word reminder from words looked up this session.
        """
        bot.reply_to(message, help_text, parse_mode='Markdown')
        logger.info(f"Sent help message to user {message.from_user.id}")
    except telebot.apihelper.ApiException as e: 
        logger.error(f"API Error in send_help for user {message.from_user.id}: {e}")
        bot.reply_to(message, "Sorry, there was an error processing your /help command.")
    except Exception as e:
        logger.error(f"Unexpected error in send_help for user {message.from_user.id}: {e}", exc_info=True)
        bot.reply_to(message, "An unexpected error occurred. Please try again later.")

@bot.message_handler(commands=['showwords'])
def show_all_words(message: types.Message, page: int = 1, user_id: Optional[int] = None) -> None:
    try:
        is_callback = not isinstance(message, types.Message)
        
        effective_user_id: int
        if user_id is None:
            effective_user_id = message.from_user.id
            if not is_callback: 
                log_request(message) 
        else:
            effective_user_id = user_id
        
        limit = 5
        offset = (page - 1) * limit
        
        logger.info(f"Showing words for user_id={effective_user_id}, page={page}")
        
        # Assuming get_words_from_db returns list of word strings if get_objects=False
        words_list: List[str] = get_words_from_db(effective_user_id, limit, offset, sort=True, get_objects=False) # type: ignore
        total_words = get_word_count(effective_user_id)
        
        chat_id = message.message.chat.id if is_callback else message.chat.id
        message_id_to_edit = message.message.message_id if is_callback else None

        if not words_list and page == 1:
            logger.info(f"User {effective_user_id}'s dictionary is empty.")
            text_to_send = "Your dictionary is empty."
            if is_callback and message_id_to_edit:
                bot.edit_message_text(text_to_send, chat_id, message_id_to_edit, reply_markup=None)
            else:
                bot.send_message(chat_id, text_to_send)
            if is_callback: bot.answer_callback_query(message.id)
            return
        elif not words_list:
            logger.info(f"No more words for user {effective_user_id} on page {page}.")
            if is_callback: bot.answer_callback_query(message.id, "No more words to display.")
            else: bot.send_message(chat_id, "No more words to display on this page.")
            return

        markup = types.InlineKeyboardMarkup()
        for word_text in words_list:
            btn_data = f"{CALLBACK_PREFIX_DEFINE}{word_text}_{effective_user_id}"
            markup.add(types.InlineKeyboardButton(word_text, callback_data=btn_data))
        
        pagination_buttons = []
        if page > 1:
            prev_data = f"{CALLBACK_PREFIX_PAGE}{page-1}_{effective_user_id}"
            pagination_buttons.append(types.InlineKeyboardButton("<< Prev", callback_data=prev_data))
        if total_words > page * limit:
            next_data = f"{CALLBACK_PREFIX_PAGE}{page+1}_{effective_user_id}"
            pagination_buttons.append(types.InlineKeyboardButton("Next >>", callback_data=next_data))
        if pagination_buttons: markup.row(*pagination_buttons)
        
        message_text = f"Your words (page {page}):"
        if is_callback and message_id_to_edit:
            bot.edit_message_text(message_text, chat_id, message_id_to_edit, reply_markup=markup)
        else:
            bot.send_message(chat_id, message_text, reply_markup=markup)
        
        if is_callback: bot.answer_callback_query(message.id)
        logger.info(f"Displayed words (page {page}) to user {effective_user_id}")

    except telebot.apihelper.ApiException as e:
        logger.error(f"API Error in show_all_words (user {user_id}, page {page}): {e}")
        # ... (error handling as before) ...
    except Exception as e:
        logger.error(f"Unexpected error in show_all_words (user {user_id}, page {page}): {e}", exc_info=True)
        # ... (error handling as before) ...

@bot.message_handler(commands=['quiz'])
def handle_quiz_command(message: types.Message) -> None:
    user_id = message.from_user.id
    chat_id = message.chat.id
    log_request(message)
    logger.info(f"User {user_id} initiated /quiz command.")
    _send_quiz_question(user_id, chat_id)

def _send_quiz_question(user_id: int, chat_id: int, message_id_to_edit: Optional[int] = None) -> None:
    quiz_question_data: Optional[Dict[str, Any]] = generate_quiz_question(user_id)

    if quiz_question_data is None:
        no_quiz_message = f"I couldn't generate a quiz. You need at least {MIN_WORDS_FOR_QUIZ} words in your dictionary."
        if message_id_to_edit: bot.edit_message_text(no_quiz_message, chat_id, message_id_to_edit, reply_markup=None)
        else: bot.send_message(chat_id, no_quiz_message)
        if user_id in current_quiz_data: del current_quiz_data[user_id]
        return

    current_quiz_data[user_id] = quiz_question_data
    word_to_ask = quiz_question_data["word"]
    options = quiz_question_data["options"]

    markup = types.InlineKeyboardMarkup()
    for i, option_text in enumerate(options):
        button_text = option_text[:80] + "..." if len(option_text) > 80 else option_text
        callback_data_quiz = f"{CALLBACK_PREFIX_QUIZ_ANSWER}{word_to_ask}_{i}_{user_id}"
        if len(callback_data_quiz.encode('utf-8')) > 64:
            callback_data_quiz = f"{CALLBACK_PREFIX_QUIZ_ANSWER}{user_id}_{i}" # Fallback
        markup.add(types.InlineKeyboardButton(button_text, callback_data=callback_data_quiz))

    quiz_message_text = f"**Quiz Time!** 🧠\n\nWhat is the definition of: *{word_to_ask}*?"
    if message_id_to_edit: bot.edit_message_text(quiz_message_text, chat_id, message_id_to_edit, reply_markup=markup, parse_mode='Markdown')
    else: bot.send_message(chat_id, quiz_message_text, reply_markup=markup, parse_mode='Markdown')
    logger.info(f"Sent quiz question for '{word_to_ask}' to user {user_id}.")

# --- Callback Query Handlers ---
def _parse_callback_data(call_data: str) -> Tuple[str, str, Optional[int], Optional[str]]:
    parts = call_data.split("_")
    action = parts[0]
    value = ""
    user_id = None
    secondary_value = None # For option_index in quiz

    action_prefix = action + "_"
    if action_prefix in [CALLBACK_PREFIX_DEFINE, CALLBACK_PREFIX_DELETE, CALLBACK_PREFIX_ADD]:
        if len(parts) >= 2 and parts[-1].isdigit():
            user_id = int(parts[-1])
            value = "_".join(parts[1:-1]) 
    elif action_prefix == CALLBACK_PREFIX_PAGE:
        if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
            value = parts[1] 
            user_id = int(parts[2])
    elif action_prefix == CALLBACK_PREFIX_QUIZ_ANSWER:
        if len(parts) == 4 and parts[2].isdigit() and parts[3].isdigit(): 
            value = parts[1] 
            secondary_value = parts[2] 
            user_id = int(parts[3])
        elif len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit(): 
            user_id = int(parts[1])
            secondary_value = parts[2] 
    elif action_prefix == CALLBACK_PREFIX_NEXT_QUIZ:
        if len(parts) == 2 and parts[1].isdigit(): user_id = int(parts[1])
    elif action == CALLBACK_PREFIX_DICTIONARY:
        if len(parts) == 2 and parts[1].isdigit(): user_id = int(parts[1])
    else: logger.warning(f"Unknown or fallback callback structure: {call_data}")
    
    return action, value, user_id, secondary_value

def handle_define_callback(call: types.CallbackQuery, word_to_define: str, user_id: int) -> None:
    logger.info(f"Action: Define word '{word_to_define}' for user {user_id}")
    if not word_to_define:
        bot.answer_callback_query(call.id, "Error: Word not specified.")
        return
    definition, audio_url = get_definition(word_to_define)
    if definition is None:
        bot.answer_callback_query(call.id, f"Could not get definition for '{word_to_define}'.")
        bot.send_message(call.message.chat.id, f"Sorry, I couldn't find a definition for '{word_to_define}'.")
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("My Dictionary", callback_data=f"{CALLBACK_PREFIX_DICTIONARY}_{user_id}"))
    markup.add(types.InlineKeyboardButton("Mark as Learned", callback_data=f"{CALLBACK_PREFIX_DELETE}{word_to_define}_{user_id}"))
    audio_file_path = get_audio_file(word_to_define, audio_url) if audio_url else None
    send_message_in_parts(call.message.chat.id, definition, word_to_define, audio_file_path, markup)
    bot.answer_callback_query(call.id)

def handle_delete_callback(call: types.CallbackQuery, word_to_delete: str, user_id: int) -> None:
    logger.info(f"Action: Delete word '{word_to_delete}' for user {user_id}")
    if not word_to_delete:
        bot.answer_callback_query(call.id, "Error: Word not specified for deletion.")
        return
    delete_word_from_db(word_to_delete, user_id)
    bot.answer_callback_query(call.id, f"'{word_to_delete}' deleted.")
    show_all_words(call, page=1, user_id=user_id) # Refresh list

def handle_add_callback(call: types.CallbackQuery, word_to_add: str, user_id: int) -> None:
    logger.info(f"Action: Add word '{word_to_add}' for user {user_id}")
    if not word_to_add:
        bot.answer_callback_query(call.id, "Error: Word not specified for adding.")
        return
    add_word_to_db(word_to_add, user_id)
    bot.answer_callback_query(call.id, f"'{word_to_add}' added.")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("View My Dictionary", callback_data=f"{CALLBACK_PREFIX_DICTIONARY}_{user_id}"))
    bot.send_message(call.message.chat.id, f"'{word_to_add}' added to your dictionary.", reply_markup=markup)

def handle_showwords_callback(call: types.CallbackQuery, user_id: int) -> None:
    logger.info(f"Action: Show words for user {user_id} (callback: {call.data})")
    show_all_words(call, page=1, user_id=user_id)

def handle_page_callback(call: types.CallbackQuery, page_num_str: str, user_id: int) -> None:
    logger.info(f"Action: Page navigation for user {user_id}, page str: '{page_num_str}'")
    if not page_num_str.isdigit():
        bot.answer_callback_query(call.id, "Error: Invalid page number.")
        return
    page = int(page_num_str)
    show_all_words(call, page, user_id=user_id)

def handle_quiz_answer_callback(call: types.CallbackQuery, word_from_cb: str, opt_idx_str: Optional[str], user_id: int) -> None:
    logger.info(f"Quiz answer from user {user_id}. Word (CB): '{word_from_cb}', Option Idx: {opt_idx_str}")
    if user_id not in current_quiz_data or opt_idx_str is None:
        bot.edit_message_text("Quiz session expired or invalid answer. Start with /quiz.", call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id, "Quiz error.")
        return

    quiz_details = current_quiz_data[user_id]
    q_word = quiz_details["word"]
    q_word_id = quiz_details["word_id"] # Get word_id for stats
    
    try:
        selected_option_idx = int(opt_idx_str)
        selected_def = quiz_details["options"][selected_option_idx]
    except (ValueError, IndexError):
        logger.error(f"Invalid option index or data for quiz answer: {opt_idx_str}")
        bot.answer_callback_query(call.id, "Error processing answer.")
        return

    is_correct = check_quiz_answer(q_word, selected_def, quiz_details["correct_definition_text"])
    update_word_quiz_stats(user_id, q_word_id, is_correct) # Update stats

    feedback = f"Correct! ✅\n\n*{q_word}* means:\n_{quiz_details['correct_definition_text']}_" if is_correct \
               else f"Not quite! ❌\n\nThe correct definition for *{q_word}* is:\n_{quiz_details['correct_definition_text']}_"
    
    if user_id in current_quiz_data: del current_quiz_data[user_id] # Clear current quiz

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Next Quiz Question ➡️", callback_data=f"{CALLBACK_PREFIX_NEXT_QUIZ}{user_id}"))
    bot.edit_message_text(feedback, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call: types.CallbackQuery) -> None:
    effective_user_id: int = call.from_user.id 
    action_for_logging: str = "unknown"
    try:
        log_request(call) 
        logger.info(f"Received callback. Data: '{call.data}', User: {call.from_user.id}")
        action, value, parsed_user_id, secondary_value = _parse_callback_data(call.data)
        action_for_logging = action
        if parsed_user_id is not None: effective_user_id = parsed_user_id
        
        logger.info(f"Parsed CB: Action='{action}', Value='{value}', User={effective_user_id}, SecVal='{secondary_value}'")

        if action == CALLBACK_PREFIX_DEFINE[:-1]: handle_define_callback(call, value, effective_user_id)
        elif action == CALLBACK_PREFIX_DELETE[:-1]: handle_delete_callback(call, value, effective_user_id)
        elif action == CALLBACK_PREFIX_ADD[:-1]: handle_add_callback(call, value, effective_user_id)
        elif action == CALLBACK_PREFIX_DICTIONARY: handle_showwords_callback(call, effective_user_id)
        elif action == CALLBACK_PREFIX_PAGE[:-1]: handle_page_callback(call, value, effective_user_id)
        elif action == CALLBACK_PREFIX_QUIZ_ANSWER[:-1]: handle_quiz_answer_callback(call, value, secondary_value, effective_user_id)
        elif action == CALLBACK_PREFIX_NEXT_QUIZ[:-1]:
            _send_quiz_question(effective_user_id, call.message.chat.id, message_id_to_edit=call.message.message_id)
            bot.answer_callback_query(call.id) 
        else:
            logger.warning(f"Unknown CB action '{action}'. Data: {call.data}")
            bot.answer_callback_query(call.id, "Unknown action.")
    except Exception as e: # General exception catch
        logger.error(f"Error in callback_inline (Action: {action_for_logging}, Data: {call.data}): {e}", exc_info=True)
        bot.answer_callback_query(call.id, "An error occurred processing your request.")

# --- Message Processing Logic ---
@bot.message_handler(func=lambda message: True)
def process_user_input(message: types.Message) -> None:
    user_id: int = message.from_user.id
    chat_id: int = message.chat.id 
    processed_text: str = message.text.lower().strip()

    try:
        log_request(message) 
        logger.info(f"Processing input. User: {user_id}, Text: '{processed_text}'")

        if not processed_text:
            logger.info(f"Empty message from user {user_id}.")
            return 

        if processed_text.startswith('/translate'): _handle_translate_message(message, processed_text)
        elif processed_text.startswith('/reminder'): _handle_reminder_message(message, processed_text)
        elif processed_text.startswith('/add'): _handle_add_message(message, processed_text)
        elif processed_text.startswith('/remove'): _handle_remove_message(message, processed_text)
        elif processed_text.startswith('/quiz'): handle_quiz_command(message)
        elif processed_text.startswith('/'): 
            logger.warning(f"Unknown command '{processed_text}' from user {user_id}.")
            bot.reply_to(message, f"Sorry, I don't recognize '{processed_text}'. Try /help.")
        else: _handle_word_definition_message(message, processed_text)
    except Exception as e:
        logger.error(f"Error processing input (User: {user_id}, Text: '{processed_text}'): {e}", exc_info=True)
        bot.reply_to(message, "An unexpected error occurred. Please try again.")

def _handle_add_message(message: types.Message, text: str) -> None:
    user_id = message.from_user.id
    command_parts = text.split(' ', 1)
    if len(command_parts) < 2 or not command_parts[1].strip():
        bot.reply_to(message, "Usage: `/add [word]` (e.g., `/add example`)", parse_mode='Markdown')
        return
    word_to_add = command_parts[1].strip().lower()
    add_word_to_db(word_to_add, user_id) # Assumes DB errors are caught inside
    bot.reply_to(message, f"Added '{word_to_add}' to your dictionary!")
    logger.info(f"Added '{word_to_add}' for user {user_id} via command.")

def _handle_remove_message(message: types.Message, text: str) -> None:
    user_id = message.from_user.id
    command_parts = text.split(' ', 1)
    if len(command_parts) < 2 or not command_parts[1].strip():
        bot.reply_to(message, "Usage: `/remove [word]` (e.g., `/remove example`)", parse_mode='Markdown')
        return
    word_to_remove = command_parts[1].strip().lower()
    
    initial_count = get_word_count(user_id)
    delete_word_from_db(word_to_remove, user_id)
    final_count = get_word_count(user_id)

    if initial_count > final_count:
        bot.reply_to(message, f"Removed '{word_to_remove}' from your dictionary!")
        logger.info(f"Removed '{word_to_remove}' for user {user_id} via command.")
    else:
        bot.reply_to(message, f"Could not find '{word_to_remove}' in your dictionary.")
        logger.info(f"'{word_to_remove}' not found for user {user_id} (manual remove).")

def _handle_translate_message(message: types.Message, text: str) -> None:
    user_id = message.from_user.id
    chat_id = message.chat.id
    parts = text.split(' ', 1)
    if len(parts) < 2 or not parts[1].strip():
        bot.reply_to(message, "Usage: `/translate [word]`")
        return
    word = parts[1].strip()
    translation = get_translation(word)
    if translation: send_message_in_parts(chat_id, f"Translation of '{word}': '{translation}'.", word)
    else: send_message_in_parts(chat_id, f"Translation not found for '{word}'.", word)

def _handle_reminder_message(message: types.Message, text: str) -> None:
    user_id = message.from_user.id
    chat_id = message.chat.id
    if not local_dictionary:
         bot.reply_to(message, "Reminder list is empty. Look up words to add them.")
         return
    random_word = random.choice(list(local_dictionary.keys()))
    local_dictionary[random_word] = time.time()
    send_message_in_parts(chat_id, f"Reminder: {random_word}", random_word)

def _handle_word_definition_message(message: types.Message, text: str) -> None:
    user_id = message.from_user.id
    chat_id = message.chat.id
    word = text # Text is the word to define
    
    definition, audio_url = get_definition(word)
    if definition is None:
        bot.reply_to(message, f"Sorry, no definition found for '{word}'.")
        return

    local_dictionary[word] = time.time()
    audio_path = get_audio_file(word, audio_url) if audio_url else None
    send_message_in_parts(chat_id, definition, word, audio_path=audio_path)
    
    markup = types.InlineKeyboardMarkup()
    cb_data = f"{CALLBACK_PREFIX_ADD}{word}_{user_id}"
    if len(cb_data.encode('utf-8')) <= 64:
        markup.add(types.InlineKeyboardButton("Add to My Dictionary", callback_data=cb_data))
        bot.send_message(chat_id, f"Add '{word}' to your dictionary?", reply_markup=markup)
    else:
        logger.warning(f"Callback data too long for 'add' button: word '{word}'")

def send_message_in_parts(chat_id: int, text: str, word: str, audio_path: Optional[str]=None, markup: Optional[types.InlineKeyboardMarkup]=None, max_length: int=3800) -> None:
    try:
        full_text = text
        if not audio_path: 
            full_text += f"\n\nListen to '{word}' on Youglish: https://youglish.com/pronounce/{word}/english"
        full_text = format_text(full_text)

        parts = [full_text[i:i + max_length] for i in range(0, len(full_text), max_length)]
        
        for i, part_text in enumerate(parts):
            is_last = (i == len(parts) - 1)
            current_markup = markup if is_last and not audio_path else None
            if audio_path and is_last and len(part_text) <= 1024: continue 
            bot.send_message(chat_id, part_text, parse_mode='Markdown', reply_markup=current_markup)

        if audio_path:
            caption = parts[-1] if parts and len(parts[-1]) <= 1024 else f"Pronunciation for '{word}'"
            try:
                with open(audio_path, 'rb') as audio_f:
                    bot.send_audio(chat_id, audio_f, caption=caption[:1024], parse_mode='Markdown', reply_markup=markup)
                logger.info(f"Sent audio for '{word}' to chat {chat_id}.")
            except FileNotFoundError: logger.error(f"Audio file not found: {audio_path}")
            except Exception as e_audio: logger.error(f"Error sending audio for '{word}': {e_audio}")
        logger.info(f"Sent message parts for '{word}' to chat {chat_id}.")
    except Exception as e:
        logger.error(f"Error in send_message_in_parts for '{word}': {e}", exc_info=True)

# --- Bot Start ---
if __name__ == "__main__":
    logger.info("Initializing LexiLearn Bot...")
    # local_dictionary initialization is above
    
    logger.info("Starting bot polling...")
    try:
        bot.polling(none_stop=True, interval=0, timeout=30)
    except Exception as e: # Catch all exceptions during polling
        logger.critical(f"Bot polling loop encountered a critical error: {e}", exc_info=True)
    finally:
        logger.info("Bot polling has stopped.")
