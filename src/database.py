import os
import psycopg2
from psycopg2 import OperationalError
from dotenv import load_dotenv
import logging

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
        logging.info("Connected to database successfully")
        return conn
    except OperationalError as e:
        logging.error(f"The error '{e}' occurred")
        return None

def add_word_to_db(word, user_id):
    conn = connect_to_db()
    cursor = conn.cursor()
    logging.info(f"add_word_to_db called with word={word}, user_id={user_id}")

    cursor.execute("SELECT user_id FROM Users WHERE user_id = %s", (user_id,))
    existing_user_id = cursor.fetchone()
    
    if existing_user_id is None:
        cursor.execute("INSERT INTO Users (user_id) VALUES (%s)", (user_id,))
        logging.info(f"Added new user: {user_id}")

    cursor.execute("SELECT word_id FROM Words WHERE word = %s", (word,))
    word_id = cursor.fetchone()
    
    if word_id is None:
        cursor.execute("INSERT INTO Words (word) VALUES (%s) RETURNING word_id", (word,))
        word_id = cursor.fetchone()[0]
        logging.info(f"Added new word: {word} with id: {word_id}")
    else:
        word_id = word_id[0]

    cursor.execute("INSERT INTO UserWords (user_id, word_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (user_id, word_id))
    logging.info(f"Linked user {user_id} with word {word} (id: {word_id})")

    conn.commit()
    cursor.close()
    conn.close()

def delete_word_from_db(word, user_id):
    conn = connect_to_db()
    cursor = conn.cursor()
    logging.info(f"delete_word_from_db called with word={word}, user_id={user_id}")

    cursor.execute("SELECT word_id FROM Words WHERE word = %s", (word,))
    word_id = cursor.fetchone()
    if word_id:
        word_id = word_id[0]
        cursor.execute("DELETE FROM UserWords WHERE user_id = %s AND word_id = %s", (user_id, word_id))
        logging.info(f"Deleted word {word} (id: {word_id}) for user {user_id}")

    conn.commit()
    cursor.close()
    conn.close()

def get_words_from_db(user_id, limit, offset, sort=False):
    conn = connect_to_db()
    cursor = conn.cursor()
    logging.info(f"get_words_from_db called with user_id={user_id}, limit={limit}, offset={offset}, sort={sort}")

    query = """
    SELECT w.word FROM Words w
    INNER JOIN UserWords uw ON w.word_id = uw.word_id
    WHERE uw.user_id = %s
    """
    if sort:
        query += " ORDER BY w.word"
    query += " LIMIT %s OFFSET %s"
    
    cursor.execute(query, (user_id, limit, offset))
    
    words = cursor.fetchall()
    logging.info(f"Fetched words for user {user_id}: {words}")
    cursor.close()
    conn.close()
    return [word[0] for word in words]

def get_word_count(user_id):
    conn = connect_to_db()
    cursor = conn.cursor()
    logging.info(f"get_word_count called with user_id={user_id}")

    cursor.execute("""
    SELECT COUNT(*) FROM UserWords uw
    WHERE uw.user_id = %s
    """, (user_id,))
    
    count = cursor.fetchone()[0]
    logging.info(f"Word count for user {user_id}: {count}")
    cursor.close()
    conn.close()
    return count

def update_audio_link(word, audio_path):
    conn = connect_to_db()
    cursor = conn.cursor()
    logging.info(f"update_audio_link called with word={word}, audio_path={audio_path}")

    cursor.execute("UPDATE Words SET audio_path = %s WHERE word = %s", (audio_path, word))

    conn.commit()
    cursor.close()
    conn.close()

def get_audio_path(word):
    conn = connect_to_db()
    cursor = conn.cursor()
    logging.info(f"get_audio_path called with word={word}")

    cursor.execute("SELECT audio_path FROM Words WHERE word = %s", (word,))
    audio_path = cursor.fetchone()
    cursor.close()
    conn.close()
    if audio_path:
        return audio_path[0]
    return None
