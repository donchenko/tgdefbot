import os
import psycopg2
from psycopg2 import OperationalError
from dotenv import load_dotenv

load_dotenv()

def connect_to_db():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        return conn
    except OperationalError as e:
        print(f"The error '{e}' occurred")
        return None

def add_word_to_db(word, user_id):
    conn = connect_to_db()
    cursor = conn.cursor()

    # Проверяем, существует ли уже этот пользователь в таблице Users
    cursor.execute("SELECT user_id FROM Users WHERE user_id = %s", (user_id,))
    existing_user_id = cursor.fetchone()
    
    if existing_user_id is None:
        # Добавляем пользователя в таблицу Users, если его там нет
        cursor.execute("INSERT INTO Users (user_id) VALUES (%s)", (user_id,))

    # Проверяем, существует ли уже это слово в таблице Words
    cursor.execute("SELECT word_id FROM Words WHERE word = %s", (word,))
    word_id = cursor.fetchone()
    
    if word_id is None:
        # Добавляем слово в таблицу Words, если его там нет
        cursor.execute("INSERT INTO Words (word) VALUES (%s) RETURNING word_id", (word,))
        word_id = cursor.fetchone()[0]
    else:
        word_id = word_id[0]

    # Добавляем связь между пользователем и словом в таблицу UserWords
    cursor.execute("INSERT INTO UserWords (user_id, word_id) VALUES (%s, %s)", (user_id, word_id))

    conn.commit()
    cursor.close()
    conn.close()


def get_all_words_from_db(user_id):
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT Words.word FROM UserWords
        JOIN Words ON UserWords.word_id = Words.word_id
        WHERE UserWords.user_id = %s
    """, (user_id,))
    words = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return words


def remove_word_from_db(word, user_id):
    conn = connect_to_db()
    # Logic to remove word from database
    pass

def find_word_in_db(word):
    conn = connect_to_db()
    # Logic to find word in database
    pass
