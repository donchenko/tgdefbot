import psycopg2
import os
from psycopg2 import OperationalError
from dotenv import load_dotenv
import logging

load_dotenv()

def create_tables():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        cursor = conn.cursor()

        # Create Users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            user_id INTEGER PRIMARY KEY,
            username VARCHAR(255),
            first_name VARCHAR(255),
            last_name VARCHAR(255)
        );
        """)

        # Create Words table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Words (
            word_id SERIAL PRIMARY KEY,
            word VARCHAR(255) NOT NULL,
            part_of_speech VARCHAR(255),
            definition TEXT,
            example TEXT,
            pronunciation VARCHAR(255),
            audio_link VARCHAR(255),
            audio_path VARCHAR(255)  -- Add the new column here
        );
        """)

        # Create UserWords table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS UserWords (
            user_id INTEGER REFERENCES Users(user_id),
            word_id INTEGER REFERENCES Words(word_id),
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, word_id)
        );
        """)

        conn.commit()
        cursor.close()
        conn.close()
        logging.info("Tables created successfully.")
    except OperationalError as e:
        logging.error(f"The error '{e}' occurred")

if __name__ == "__main__":
    create_tables()
