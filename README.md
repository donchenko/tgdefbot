# LexiLearn Telegram Bot

LexiLearn is a Telegram bot designed to help users expand their English vocabulary by providing definitions, pronunciations, usage examples, and managing a personal dictionary of learned words.

## Features

*   **Word Definitions**: Get detailed definitions, parts of speech, pronunciations (text and audio), and usage examples for English words using the Merriam-Webster Learners API.
*   **Personal Dictionary**: Users can add words they are learning to a personal dictionary and view them.
*   **Interactive Learning**:
    *   Inline buttons for quick actions like adding words or marking them as learned.
    *   (Planned for future) Quiz functionality to test vocabulary.
*   **Improved User Experience**:
    *   Comprehensive `/help` command.
    *   Clear feedback messages for user interactions.
    *   User-friendly welcome message and button text.
*   **Robust Backend**:
    *   Enhanced error handling for API calls, database operations, and user input.
    *   Structured code for better maintainability.
    *   Security considerations implemented (environment variables for secrets, input sanitization for file paths).

## Setup

1.  **Prerequisites**:
    *   Python 3.10 or higher.
    *   PostgreSQL database server.

2.  **Clone the Repository**:
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```
    (Replace `<repository_url>` and `<repository_directory>` with actual values)

3.  **Install Dependencies**:
    Create a virtual environment (recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
    Install required packages:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Environment Variables**:
    Create a `.env` file in the root directory of the project and add the following variables:
    ```env
    TOKEN=<YOUR_TELEGRAM_BOT_TOKEN>
    MERRIAM_WEBSTER_API_KEY=<YOUR_MERRIAM_WEBSTER_API_KEY>
    
    DB_NAME=<YOUR_DATABASE_NAME>
    DB_USER=<YOUR_DATABASE_USER>
    DB_PASSWORD=<YOUR_DATABASE_PASSWORD>
    DB_HOST=localhost 
    DB_PORT=5432 
    ```
    Replace placeholders with your actual credentials.
    *   `TOKEN`: Your Telegram Bot token from BotFather.
    *   `MERRIAM_WEBSTER_API_KEY`: Your API key for the Merriam-Webster Learners Dictionary.
    *   `DB_*`: Your PostgreSQL database connection details.

5.  **Initialize Database Schema**:
    Run the database initialization script to create the necessary tables:
    ```bash
    python src/db_init.py
    ```
    Ensure your PostgreSQL server is running and accessible with the credentials provided in `.env` before running this script.

## Running the Bot

Once the setup is complete, you can run the bot using:

```bash
python main.py
```

The bot will start polling for messages.

## Available Commands

*   `/start` - Displays the welcome message.
*   `/help` - Shows a detailed help message with all available commands and how to use the bot.
*   `/showwords` - View all words currently in your personal dictionary. Supports pagination.
*   `/add [word]` - Manually add a specific word to your dictionary (e.g., `/add lexicon`).
*   `/remove [word]` - Manually remove a specific word from your dictionary (e.g., `/remove lexicon`).
*   `/quiz` - (Partially Implemented) Allows users to request a one-off quiz question based on their dictionary. The backend logic for more advanced quiz features (scheduling, spaced repetition) exists but is not yet fully user-facing.
*   `/translate [word]` - (Experimental) Get an English-to-Russian translation for a word.
*   `/reminder` - Get a random word reminder from a temporary list of words you've looked up in the current session.

You can also simply type any English word and send it to the bot to get its definition and pronunciation.

## Testing

The project includes a suite of unit tests. To run the tests:

1.  Ensure you have installed all dependencies from `requirements.txt` (including development/testing dependencies if specified separately in a larger project).
2.  The tests use mocking for external services and environment variables, so they can be run without live API keys or a running database for most parts. However, ensure Python can import all necessary modules (e.g., `psycopg2-binary`, `python-dotenv` should be available in the test environment).
3.  Run the tests using the `unittest` module from the root directory of the project:

    ```bash
    python -m unittest test_bot.py
    ```
    Alternatively, for test discovery (if tests are in multiple files or a `tests` directory):
    ```bash
    python -m unittest discover
    ```

## Development Notes

*   **Quiz Feature**: The backend logic for quiz generation (`src/quiz_handler.py`) and related database structures (`UserQuizPreferences`, `UserQuizStats`) for spaced repetition and scheduling are implemented. The current user-facing `/quiz` command provides on-demand questions. Full integration of scheduling and user preference management for quizzes is planned for future development.
*   **Error Handling**: The bot includes improved error handling for API interactions, database operations, and user inputs. Errors are logged to `bot.log` and to the console.
*   **Security**: Secrets are managed via environment variables (`.env` file). Basic input sanitization is in place for file paths (audio downloads). Database queries use parameterization to prevent SQL injection.
```
