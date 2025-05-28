import unittest
from unittest.mock import patch, MagicMock, call 
import time 
import requests # For requests.exceptions used in get_definition tests
import os # For patching os.environ

# Import functions to be tested
from src.utilities import format_text, get_definition

# --- Tests for src/utilities.py ---

class TestFormatText(unittest.TestCase):
    def test_empty_input(self):
        self.assertEqual(format_text(""), "")
        self.assertEqual(format_text(None), "")

    def test_italic_formatting(self):
        self.assertEqual(format_text("This is {it}italic{/it}."), "This is _italic_.")
        self.assertEqual(format_text("{it}italic{/it} at start."), "_italic_ at start.")
        self.assertEqual(format_text("End with {it}italic{/it}"), "End with _italic_")

    def test_bold_formatting(self): 
        self.assertEqual(format_text("This is {b}bold{/b}."), "This is *bold*.")
        self.assertEqual(format_text("This is {phrase}bold_phrase{/phrase}."), "This is *bold_phrase*.")

    def test_mixed_formatting(self):
        self.assertEqual(format_text("Text with {it}italic{/it} and {b}bold{/b}."), "Text with _italic_ and *bold*.")

    def test_unpaired_tags(self):
        self.assertEqual(format_text("Unpaired {it}italic tag."), "Unpaired _italic tag.") 
        self.assertEqual(format_text("Another {it}one."), "Another _one.") 
        self.assertEqual(format_text("Unpaired {b}bold."), "Unpaired *bold.") 
        self.assertEqual(format_text("Mixture of unpaired {it}a{/it} and {b}b."), "Mixture of unpaired _a_ and *b.") 
        self.assertEqual(format_text("Mixture of unpaired {it}a and {b}b."), "Mixture of unpaired _a and *b.")

    def test_no_tags(self):
        self.assertEqual(format_text("This is plain text."), "This is plain text.")

    def test_other_tags_removal(self): 
        self.assertEqual(format_text("Text with {inf}subscript{/inf}."), "Text with subscript.")
        self.assertEqual(format_text("Text with {sup}superscript{/sup}."), "Text with superscript.")

    def test_cleanup_spaces_and_colons(self):
        self.assertEqual(format_text("Word : definition"), "Word: definition")
        self.assertEqual(format_text("Text  with   multiple spaces."), "Text with multiple spaces.")
        self.assertEqual(format_text("Complex {it}case{/it} :  multiple   {b}issues{/b}."), "Complex _case_: multiple *issues*.")


class TestGetDefinition(unittest.TestCase):
    @patch('src.utilities.requests.get')
    @patch('src.utilities.log_request') 
    def test_get_definition_success_full_data(self, mock_log_request_util, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_api_data = [
            {
                "fl": "noun", 
                "shortdef": ["def1.", "def2."],
                "hwi": {"prs": [{"mw": "ig-ˈzam-pəl", "sound": {"audio": "example01"}}]},
                "def": [{"sseq": [[["sense", {"dt": [["text", "usage "], ["vis", [{"t": "good {it}example{/it}"}]]]}]]]} ]
            }
        ]
        mock_response.json.return_value = mock_api_data
        mock_requests_get.return_value = mock_response
        word = "example"
        definition_text, audio_link = get_definition(word)
        self.assertIn("Part of Speech: noun", definition_text)
        self.assertIn("- def1.", definition_text)
        self.assertIn("Pronunciation: ig-ˈzam-pəl", definition_text)
        self.assertIn("Usage Examples:\n- good _example_", definition_text)
        self.assertTrue(audio_link.endswith("e/example01.wav"))
        mock_log_request_util.assert_called_with("definition_api", word, success=True)

    @patch('src.utilities.requests.get')
    @patch('src.utilities.log_request')
    def test_get_definition_suggestions(self, mock_log_request_util, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = ["exampel", "exmple"]
        mock_requests_get.return_value = mock_response
        word = "exaple"
        definition_text, audio_link = get_definition(word)
        self.assertIn(f"No definition found for '{word}'. Did you mean: exampel, exmple?", definition_text)
        self.assertIsNone(audio_link)
        mock_log_request_util.assert_called_with("definition_api", word, success=True)

    @patch('src.utilities.requests.get')
    @patch('src.utilities.log_request')
    def test_get_definition_http_error_404(self, mock_log_request_util, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        http_error = requests.exceptions.HTTPError(response=mock_response)
        http_error.response = mock_response 
        mock_response.raise_for_status.side_effect = http_error
        mock_requests_get.return_value = mock_response
        word = "nonexistentword"
        definition_text, audio_link = get_definition(word)
        self.assertEqual(definition_text, f"No definition found for '{word}'. Please check the spelling.")
        self.assertIsNone(audio_link)
        mock_log_request_util.assert_called_with("definition_api", word, success=False, error_message=unittest.mock.ANY)

    @patch('src.utilities.requests.get')
    @patch('src.utilities.log_request')
    def test_get_definition_request_exception(self, mock_log_request_util, mock_requests_get):
        mock_requests_get.side_effect = requests.exceptions.ConnectionError("Connection failed")
        word = "testword"
        definition_text, audio_link = get_definition(word)
        self.assertEqual(definition_text, "Sorry, I couldn't fetch the definition due to a network or API issue.")
        self.assertIsNone(audio_link)
        mock_log_request_util.assert_called_with("definition_api", word, success=False, error_message="Connection failed")

# --- Mock Objects for main.py tests ---
class MockUser:
    def __init__(self, id, first_name="TestUser", username="testusername"):
        self.id = id
        self.first_name = first_name
        self.username = username

class MockChat:
    def __init__(self, id, type="private"):
        self.id = id
        self.type = type

class MockMessage:
    def __init__(self, text, message_id=1, from_user_id=123, chat_id=456, date=None):
        self.message_id = message_id
        self.text = text
        self.from_user = MockUser(id=from_user_id)
        self.chat = MockChat(id=chat_id)
        self.date = date if date is not None else int(time.time())
        self.message = self 

class MockCallbackQuery:
    def __init__(self, data, from_user_id=123, message=None, id="callback_id_123"):
        self.id = id
        self.from_user = MockUser(id=from_user_id)
        self.data = data
        self.message = message if message else MockMessage(text="Original message for callback", chat_id=456) 
        if not hasattr(self.message, 'chat'): 
            self.message.chat = MockChat(id=456 if not message else message.chat.id)
        if not hasattr(self.message, 'message_id'): 
            self.message.message_id = 1001 

# --- Tests for main.py ---
@patch('main.bot')    
class TestMainCommandHandlers(unittest.TestCase):

    def _get_patched_env(self):
        return {
            "TOKEN": "123456:valid_token_format", 
            "MERRIAM_WEBSTER_API_KEY": "fake_mw_api_key", 
            "DB_NAME": "test_db", 
            "DB_USER": "test_user", 
            "DB_PASSWORD": "test_password", 
            "DB_HOST": "localhost", 
            "DB_PORT": "5432"
        }

    @patch('logging.getLogger') 
    @patch('main.log_request') 
    def test_send_help_command(self, mock_main_log_request, mock_get_logger, mock_main_bot):
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance

        with patch.dict(os.environ, self._get_patched_env(), clear=True):
            import main # Import main here to ensure patches are active for its module-level code
            mock_message_obj = MockMessage(text="/help")
            main.send_help(mock_message_obj)
        
        mock_main_log_request.assert_called_once_with(mock_message_obj)
        mock_main_bot.reply_to.assert_called_once()
        args, kwargs = mock_main_bot.reply_to.call_args
        self.assertEqual(args[0], mock_message_obj)
        help_text_sent = args[1]
        self.assertIn("/add [word]", help_text_sent)
        self.assertIn("/showwords", help_text_sent)
        self.assertEqual(kwargs.get('parse_mode'), 'Markdown')
        mock_logger_instance.info.assert_any_call(f"Sent help message to user {mock_message_obj.from_user.id}")

    @patch('logging.getLogger')
    @patch('main.add_word_to_db')
    @patch('main.log_request')
    def test_process_user_input_add_word_success(self, mock_main_log_request, mock_add_db, mock_get_logger, mock_main_bot):
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance
        
        with patch.dict(os.environ, self._get_patched_env(), clear=True):
            import main
            mock_message_obj = MockMessage(text="/add exampleword")
            main.process_user_input(mock_message_obj)

        mock_main_log_request.assert_called_once_with(mock_message_obj)
        mock_add_db.assert_called_once_with("exampleword", mock_message_obj.from_user.id)
        mock_main_bot.reply_to.assert_called_once_with(mock_message_obj, "Added 'exampleword' to your dictionary!")
        mock_logger_instance.info.assert_any_call(f"Added 'exampleword' for user {mock_message_obj.from_user.id} via command.")

    @patch('logging.getLogger')
    @patch('main.log_request')
    def test_process_user_input_add_word_missing_arg(self, mock_main_log_request, mock_get_logger, mock_main_bot):
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance

        with patch.dict(os.environ, self._get_patched_env(), clear=True):
            import main
            mock_message_obj = MockMessage(text="/add ")
            main.process_user_input(mock_message_obj)

        mock_main_log_request.assert_called_once_with(mock_message_obj)
        mock_main_bot.reply_to.assert_called_once()
        args, kwargs = mock_main_bot.reply_to.call_args
        self.assertEqual(args[1], "Usage: `/add [word]` (e.g., `/add example`)")
        self.assertEqual(kwargs.get('parse_mode'), 'Markdown')
        mock_logger_instance.warning.assert_any_call(f"User {mock_message_obj.from_user.id} sent /add without a word.")

    @patch('logging.getLogger')
    @patch('main.delete_word_from_db')
    @patch('main.get_word_count') 
    @patch('main.log_request')
    def test_process_user_input_remove_word_success(self, mock_main_log_request, mock_get_count, mock_delete_db, mock_get_logger, mock_main_bot):
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance

        with patch.dict(os.environ, self._get_patched_env(), clear=True):
            import main
            mock_message_obj = MockMessage(text="/remove exampleword")
            mock_get_count.side_effect = [5, 4] 
            main.process_user_input(mock_message_obj)

        mock_main_log_request.assert_called_once_with(mock_message_obj)
        mock_delete_db.assert_called_once_with("exampleword", mock_message_obj.from_user.id)
        mock_main_bot.reply_to.assert_called_once_with(mock_message_obj, "Removed 'exampleword' from your dictionary!")
        mock_logger_instance.info.assert_any_call(f"Removed 'exampleword' for user {mock_message_obj.from_user.id} via command.")

    @patch('logging.getLogger')
    @patch('main.get_definition')
    @patch('main.get_audio_file')
    @patch('main.send_message_in_parts')
    @patch('main.log_request')
    def test_process_user_input_define_word_success(self, mock_main_log_request, mock_send_parts, mock_get_audio, mock_get_def, mock_get_logger, mock_main_bot):
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance
        
        with patch.dict(os.environ, self._get_patched_env(), clear=True):
            import main # Import main here to access main.CALLBACK_PREFIX_ADD
            mock_message_obj = MockMessage(text="erudite")
            mock_get_def.return_value = ("Definition of erudite.", "http://audio.example.com/erudite.wav")
            mock_get_audio.return_value = "/path/to/erudite.wav"
            main.process_user_input(mock_message_obj)

        mock_main_log_request.assert_called_once_with(mock_message_obj)
        mock_get_def.assert_called_once_with("erudite")
        mock_get_audio.assert_called_once_with("erudite", "http://audio.example.com/erudite.wav")
        
        # Check that send_message_in_parts was called for the definition
        mock_send_parts.assert_any_call(
            mock_message_obj.chat.id, "Definition of erudite.", "erudite", audio_path="/path/to/erudite.wav"
        )
        
        # Robust check for the "Add to Dictionary" prompt and its markup
        found_add_prompt = False
        for call_item in mock_main_bot.send_message.call_args_list:
            args, kwargs = call_item
            if len(args) > 1 and "Would you like to add this word to your dictionary?" in args[1]:
                reply_markup = kwargs.get('reply_markup')
                if reply_markup and hasattr(reply_markup, 'keyboard'):
                    for row in reply_markup.keyboard:
                        for button_obj in row:
                            if button_obj.text == "Add to My Dictionary" and \
                               hasattr(main, 'CALLBACK_PREFIX_ADD') and \
                               button_obj.callback_data.startswith(f"{main.CALLBACK_PREFIX_ADD}erudite_"):
                                found_add_prompt = True
                                break
                        if found_add_prompt:
                            break
            if found_add_prompt:
                break
        
        self.assertTrue(found_add_prompt, "The 'Add to My Dictionary' prompt with correct button was not sent.")
        mock_logger_instance.info.assert_any_call(f"Sent definition of 'erudite' and add prompt to user {mock_message_obj.from_user.id}.")

    @patch('logging.getLogger')
    @patch('main.get_definition')
    @patch('main.log_request')
    def test_process_user_input_define_word_not_found(self, mock_main_log_request, mock_get_def, mock_get_logger, mock_main_bot):
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance

        with patch.dict(os.environ, self._get_patched_env(), clear=True):
            import main
            mock_message_obj = MockMessage(text="nonexistentword")
            mock_get_def.return_value = (None, None) 
            main.process_user_input(mock_message_obj)
        
        mock_main_log_request.assert_called_once_with(mock_message_obj)
        mock_get_def.assert_called_once_with("nonexistentword")
        mock_main_bot.reply_to.assert_called_once_with(mock_message_obj, "Sorry, no definition found for 'nonexistentword'.")
        mock_logger_instance.warning.assert_any_call(f"No definition found for 'nonexistentword' for user {mock_message_obj.from_user.id}.")

if __name__ == '__main__':
    unittest.main()
