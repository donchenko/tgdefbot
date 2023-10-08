import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
import os
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)


load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

logging.info(f"DB_HOST: {DB_HOST}, DB_PORT: {DB_PORT}, DB_NAME: {DB_NAME}, DB_USER: {DB_USER}")


try:
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    logging.info("Successfully connected to the database.")
except Exception as e:
    logging.error(f"Failed to connect to the database: {e}")
    exit(1)

cursor = conn.cursor()

# Create Users table if not exists
cursor.execute("""
    CREATE TABLE IF NOT EXISTS Users (
        user_id INT PRIMARY KEY,
        username VARCHAR(255),
        first_name VARCHAR(255),
        last_name VARCHAR(255)
    );
""")

# Create Words table if not exists
cursor.execute("""
    CREATE TABLE IF NOT EXISTS Words (
        word_id SERIAL PRIMARY KEY,
        word VARCHAR(255) NOT NULL,
        part_of_speech VARCHAR(255),
        definition TEXT,
        example TEXT,
        pronunciation VARCHAR(255),
        audio_link VARCHAR(255)
    );
""")

# Create UserWords table if not exists
cursor.execute("""
    CREATE TABLE IF NOT EXISTS UserWords (
        user_id INT,
        word_id INT,
        date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES Users(user_id),
        FOREIGN KEY (word_id) REFERENCES Words(word_id),
        PRIMARY KEY (user_id, word_id)
    );
""")

conn.commit()
cursor.close()
conn.close()
