import psycopg2

def connect_to_db():
    # Your connection logic here
    pass

def add_word_to_db(word, user_id):
    conn = connect_to_db()
    # Logic to add word to database
    pass

def remove_word_from_db(word, user_id):
    conn = connect_to_db()
    # Logic to remove word from database
    pass

def find_word_in_db(word):
    conn = connect_to_db()
    # Logic to find word in database
    pass
