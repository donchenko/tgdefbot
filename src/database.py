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

def delete_word_from_db(word, user_id):
    conn = connect_to_db()  # Your function to get a database connection
    cursor = conn.cursor()

    # First, get the word_id
    cursor.execute("SELECT word_id FROM Words WHERE word = %s", (word,))
    result = cursor.fetchone()
    if result:
        word_id = result[0]

        # Now, delete the entry from UserWords
        cursor.execute("DELETE FROM UserWords WHERE user_id = %s AND word_id = %s", (user_id, word_id))
        conn.commit()

    cursor.close()
    conn.close()


def get_words_from_db(user_id, limit, offset):
    conn = connect_to_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT Words.word
        FROM Words
        JOIN UserWords ON Words.word_id = UserWords.word_id
        WHERE UserWords.user_id = %s
        LIMIT %s OFFSET %s
    """, (user_id, limit, offset))
    
    words = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return [word[0] for word in words]

def get_word_count(user_id):
    conn = connect_to_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM Words
        JOIN UserWords ON Words.word_id = UserWords.word_id
        WHERE UserWords.user_id = %s
    """, (user_id,))
    
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    
    return count


def remove_word_from_db(word, user_id):
    conn = connect_to_db()
    # Logic to remove word from database
    pass

def find_word_in_db(word):
    conn = connect_to_db()
    # Logic to find word in database
    pass
