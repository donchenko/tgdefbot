import os
import psycopg2
from psycopg2 import OperationalError
from dotenv import load_dotenv
import logging
from typing import Tuple, Optional, List, Dict, Any, Union # Added for Python 3.9 compatibility

load_dotenv()

# Ensure logger is available.
if 'logger' not in globals():
    logger = logging.getLogger(__name__)
    if not logger.hasHandlers(): 
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )

def connect_to_db() -> Optional[psycopg2.extensions.connection]:
    conn = None
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        logger.info("Connected to database successfully")
        return conn
    except (OperationalError, psycopg2.Error) as e:
        logger.error(f"The error '{e}' occurred during database connection")
        return None

def add_word_to_db(word: str, user_id: int) -> None:
    conn = None
    cursor = None
    try:
        conn = connect_to_db()
        if not conn:
            raise psycopg2.Error("Failed to connect to database")
        cursor = conn.cursor()
        logger.info(f"add_word_to_db called with word='{word}', user_id={user_id}")

        cursor.execute("SELECT user_id FROM Users WHERE user_id = %s", (user_id,))
        existing_user_id = cursor.fetchone()
        
        if existing_user_id is None:
            cursor.execute("INSERT INTO Users (user_id) VALUES (%s)", (user_id,))
            logger.info(f"Added new user: {user_id}")

        cursor.execute("SELECT word_id FROM Words WHERE word = %s", (word,))
        word_id_result = cursor.fetchone()
        
        if word_id_result is None:
            cursor.execute("INSERT INTO Words (word) VALUES (%s) RETURNING word_id", (word,))
            word_id = cursor.fetchone()[0]
            logger.info(f"Added new word: '{word}' with id: {word_id}")
        else:
            word_id = word_id_result[0]

        cursor.execute("INSERT INTO UserWords (user_id, word_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (user_id, word_id))
        logger.info(f"Linked user {user_id} with word '{word}' (id: {word_id})")

        conn.commit()
        logger.info(f"Successfully added word '{word}' for user {user_id}")
    except psycopg2.Error as e:
        logger.error(f"Database error in add_word_to_db (word='{word}', user_id={user_id}): {e}")
        if conn:
            conn.rollback() 
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        logger.info("Database connection closed in add_word_to_db")

def delete_word_from_db(word: str, user_id: int) -> None:
    conn = None
    cursor = None
    try:
        conn = connect_to_db()
        if not conn:
            raise psycopg2.Error("Failed to connect to database")
        cursor = conn.cursor()
        logger.info(f"delete_word_from_db called with word='{word}', user_id={user_id}")

        cursor.execute("SELECT word_id FROM Words WHERE word = %s", (word,))
        word_id_result = cursor.fetchone()
        if word_id_result:
            word_id = word_id_result[0]
            cursor.execute("DELETE FROM UserWords WHERE user_id = %s AND word_id = %s", (user_id, word_id))
            conn.commit()
            logger.info(f"Successfully deleted word '{word}' (id: {word_id}) for user {user_id}")
        else:
            logger.info(f"Word '{word}' not found, cannot delete for user {user_id}")
    except psycopg2.Error as e:
        logger.error(f"Database error in delete_word_from_db (word='{word}', user_id={user_id}): {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        logger.info("Database connection closed in delete_word_from_db")

def get_words_from_db(user_id: int, limit: int, offset: int, sort: bool = False, get_objects: bool = False) -> List[Union[str, Dict[str, Any]]]:
    conn = None
    cursor = None
    result_data: List[Union[str, Dict[str, Any]]] = []
    try:
        conn = connect_to_db()
        if not conn:
            raise psycopg2.Error("Failed to connect to database for get_words_from_db")
        cursor = conn.cursor()
        logger.info(f"get_words_from_db called for user_id={user_id}, limit={limit}, offset={offset}, sort={sort}, get_objects={get_objects}")

        select_clause = "w.word_id, w.word" if get_objects else "w.word"
        query = f"""
        SELECT {select_clause} FROM Words w
        INNER JOIN UserWords uw ON w.word_id = uw.word_id
        WHERE uw.user_id = %s
        """
        if sort:
            query += " ORDER BY w.word"
        query += " LIMIT %s OFFSET %s"
        
        cursor.execute(query, (user_id, limit, offset))
        
        fetched_rows = cursor.fetchall()
        if get_objects:
            result_data = [{'word_id': row[0], 'word': row[1]} for row in fetched_rows]
        else:
            result_data = [row[0] for row in fetched_rows] 
            
        logger.info(f"Fetched {len(result_data)} word entries for user {user_id} (objects: {get_objects})")
    except psycopg2.Error as e:
        logger.error(f"Database error in get_words_from_db (user_id={user_id}): {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        logger.info("Database connection closed in get_words_from_db")
        return result_data

def get_word_count(user_id: int) -> int:
    conn = None
    cursor = None
    count = 0
    try:
        conn = connect_to_db()
        if not conn:
            raise psycopg2.Error("Failed to connect to database for get_word_count")
        cursor = conn.cursor()
        logger.info(f"get_word_count called with user_id={user_id}")

        cursor.execute("SELECT COUNT(*) FROM UserWords uw WHERE uw.user_id = %s", (user_id,))
        
        count_result = cursor.fetchone()
        if count_result:
            count = count_result[0]
        logger.info(f"Word count for user {user_id}: {count}")
    except psycopg2.Error as e:
        logger.error(f"Database error in get_word_count (user_id={user_id}): {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        logger.info("Database connection closed in get_word_count")
        return count

def update_audio_link(word: str, audio_path: str) -> None:
    conn = None
    cursor = None
    try:
        conn = connect_to_db()
        if not conn:
            raise psycopg2.Error("Failed to connect to database for update_audio_link")
        cursor = conn.cursor()
        logger.info(f"update_audio_link called with word='{word}', audio_path='{audio_path}'")

        cursor.execute("UPDATE Words SET audio_path = %s WHERE word = %s", (audio_path, word))
        conn.commit()
        logger.info(f"Successfully updated audio link for word '{word}'")
    except psycopg2.Error as e:
        logger.error(f"Database error in update_audio_link (word='{word}'): {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        logger.info("Database connection closed in update_audio_link")

def get_audio_path(word: str) -> Optional[str]:
    conn = None
    cursor = None
    audio_path_result: Optional[str] = None
    try:
        conn = connect_to_db()
        if not conn:
            raise psycopg2.Error("Failed to connect to database for get_audio_path")
        cursor = conn.cursor()
        logger.info(f"get_audio_path called with word='{word}'")

        cursor.execute("SELECT audio_path FROM Words WHERE word = %s", (word,))
        audio_path_row = cursor.fetchone() 
        if audio_path_row:
            audio_path_result = audio_path_row[0]
            logger.info(f"Fetched audio path for word '{word}': {audio_path_result}")
        else:
            logger.info(f"No audio path found for word '{word}'")
    except psycopg2.Error as e:
        logger.error(f"Database error in get_audio_path (word='{word}'): {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        logger.info("Database connection closed in get_audio_path")
        return audio_path_result

# --- Quiz Preferences Functions ---

def set_user_quiz_preference(user_id: int, quiz_enabled: bool, quiz_time: Optional[str] = None) -> None:
    conn = None
    cursor = None
    try:
        conn = connect_to_db()
        if not conn:
            raise psycopg2.Error("Failed to connect to database for set_user_quiz_preference")
        cursor = conn.cursor()
        
        cursor.execute("SELECT user_id FROM Users WHERE user_id = %s", (user_id,))
        if cursor.fetchone() is None:
            logger.warning(f"User {user_id} not found in Users table. Cannot set quiz preferences.")
            return

        upsert_query = """
            INSERT INTO UserQuizPreferences (user_id, quiz_enabled, quiz_time)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
            quiz_enabled = EXCLUDED.quiz_enabled,
            quiz_time = EXCLUDED.quiz_time;
        """
        cursor.execute(upsert_query, (user_id, quiz_enabled, quiz_time))
        conn.commit()
        logger.info(f"Successfully set quiz preferences for user {user_id}. Enabled: {quiz_enabled}, Time: {quiz_time or 'Not Set'}")
    except psycopg2.Error as e:
        logger.error(f"Database error in set_user_quiz_preference for user {user_id}: {e}")
        if conn: conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        logger.info("Database connection closed in set_user_quiz_preference")

def get_user_quiz_preference(user_id: int) -> Optional[Dict[str, Any]]:
    conn = None
    cursor = None
    preference = None
    try:
        conn = connect_to_db()
        if not conn:
            raise psycopg2.Error("Failed to connect to database for get_user_quiz_preference")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, quiz_enabled, quiz_time, last_quiz_sent_at FROM UserQuizPreferences WHERE user_id = %s",
            (user_id,)
        )
        row = cursor.fetchone()
        if row:
            preference = {
                "user_id": row[0],
                "quiz_enabled": row[1],
                "quiz_time": row[2].strftime('%H:%M:%S') if row[2] else None,
                "last_quiz_sent_at": row[3]
            }
            logger.info(f"Fetched quiz preference for user {user_id}: {preference}")
        else:
            logger.info(f"No quiz preference found for user {user_id}.")
    except psycopg2.Error as e:
        logger.error(f"Database error in get_user_quiz_preference for user {user_id}: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        logger.info("Database connection closed in get_user_quiz_preference")
        return preference

def get_users_for_daily_quiz(current_time_str: str) -> List[int]:
    conn = None
    cursor = None
    user_ids: List[int] = []
    try:
        conn = connect_to_db()
        if not conn:
            raise psycopg2.Error("Failed to connect to database for get_users_for_daily_quiz")
        cursor = conn.cursor()

        time_match_condition = "quiz_time = %s"
        query_param = current_time_str
        if len(current_time_str.split(':')) == 2: 
            time_match_condition = "TEXT(quiz_time) LIKE %s" 
            query_param = current_time_str + ':%' 
        
        query = f"""
            SELECT user_id FROM UserQuizPreferences
            WHERE quiz_enabled = TRUE
            AND {time_match_condition}
            AND (last_quiz_sent_at IS NULL OR last_quiz_sent_at < CURRENT_DATE);
        """
        cursor.execute(query, (query_param,))
        rows = cursor.fetchall()
        user_ids = [row[0] for row in rows]
        logger.info(f"Found {len(user_ids)} users for daily quiz at time matching '{current_time_str}': {user_ids}")
    except psycopg2.Error as e:
        logger.error(f"Database error in get_users_for_daily_quiz (time: {current_time_str}): {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        logger.info("Database connection closed in get_users_for_daily_quiz")
        return user_ids

def update_last_quiz_sent_at(user_id: int, timestamp: Any) -> None: # timestamp should be datetime object or ISO string
    conn = None
    cursor = None
    try:
        conn = connect_to_db()
        if not conn:
            raise psycopg2.Error("Failed to connect to database for update_last_quiz_sent_at")
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE UserQuizPreferences SET last_quiz_sent_at = %s WHERE user_id = %s",
            (timestamp, user_id)
        )
        conn.commit()
        if cursor.rowcount > 0:
            logger.info(f"Updated last_quiz_sent_at for user {user_id} to {timestamp}")
        else:
            logger.warning(f"Failed to update last_quiz_sent_at for user {user_id} (user not found or no change needed).")
    except psycopg2.Error as e:
        logger.error(f"Database error in update_last_quiz_sent_at for user {user_id}: {e}")
        if conn: conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        logger.info("Database connection closed in update_last_quiz_sent_at")

# --- Quiz Stats Functions ---

def update_word_quiz_stats(user_id: int, word_id: int, was_correct: bool) -> None:
    conn = None
    cursor = None
    try:
        conn = connect_to_db()
        if not conn:
            raise psycopg2.Error("Failed to connect to database for update_word_quiz_stats")
        cursor = conn.cursor()
        
        correct_increment = 1 if was_correct else 0
        incorrect_increment = 1 if not was_correct else 0
        
        query = """
            INSERT INTO UserQuizStats (user_id, word_id, times_correct, times_incorrect, last_seen_in_quiz_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, word_id) DO UPDATE SET
            times_correct = UserQuizStats.times_correct + EXCLUDED.times_correct,
            times_incorrect = UserQuizStats.times_incorrect + EXCLUDED.times_incorrect,
            last_seen_in_quiz_at = EXCLUDED.last_seen_in_quiz_at;
        """
        cursor.execute(query, (user_id, word_id, correct_increment, incorrect_increment))
        conn.commit()
        logger.info(f"Updated quiz stats for user {user_id}, word_id {word_id}. Correct: {was_correct}")
    except psycopg2.Error as e:
        logger.error(f"Database error in update_word_quiz_stats (user: {user_id}, word: {word_id}): {e}")
        if conn: conn.rollback()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        logger.info("Database connection closed in update_word_quiz_stats")

def get_least_tested_words(user_id: int, count: int = 5) -> List[int]:
    conn = None
    cursor = None
    word_ids: List[int] = []
    try:
        conn = connect_to_db()
        if not conn:
            raise psycopg2.Error("Failed to connect to database for get_least_tested_words")
        cursor = conn.cursor()
        
        query = """
            SELECT uw.word_id
            FROM UserWords uw
            LEFT JOIN UserQuizStats uqs ON uw.word_id = uqs.word_id AND uw.user_id = uqs.user_id
            WHERE uw.user_id = %s
            ORDER BY
                COALESCE(uqs.last_seen_in_quiz_at, '1970-01-01') ASC,
                (CASE 
                    WHEN COALESCE(uqs.times_correct + uqs.times_incorrect, 0) = 0 THEN 0 
                    ELSE (CAST(uqs.times_correct AS FLOAT) / (uqs.times_correct + uqs.times_incorrect)) 
                 END) ASC,
                RANDOM()
            LIMIT %s;
        """
        cursor.execute(query, (user_id, count))
        rows = cursor.fetchall()
        word_ids = [row[0] for row in rows]
        logger.info(f"Fetched {len(word_ids)} least tested word_ids for user {user_id}: {word_ids}")
    except psycopg2.Error as e:
        logger.error(f"Database error in get_least_tested_words for user {user_id}: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        logger.info("Database connection closed in get_least_tested_words")
        return word_ids
