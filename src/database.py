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

def add_word_to_db(word, definition, user_id):
    conn = connect_to_db()
    cursor = conn.cursor()
    query = "INSERT INTO user_dictionary (user_id, word, definition) VALUES (%s, %s, %s)"
    cursor.execute(query, (user_id, word, definition))
    conn.commit()
    cursor.close()
    conn.close()


def remove_word_from_db(word, user_id):
    conn = connect_to_db()
    # Logic to remove word from database
    pass

def find_word_in_db(word):
    conn = connect_to_db()
    # Logic to find word in database
    pass
