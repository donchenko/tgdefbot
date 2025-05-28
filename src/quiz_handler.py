import random
import logging
from typing import Tuple, Optional, List, Dict, Any, Union # Added for Python 3.9 compatibility
# from src.database import get_least_tested_words, get_words_from_db 
from src.utilities import get_definition 

logger = logging.getLogger(__name__)

# Min words needed in user's dictionary to generate a meaningful quiz.
MIN_WORDS_FOR_QUIZ = 2  # For at least one correct and one distractor. User must have this many words.
# Number of choices for the multiple choice question (1 correct + (NUM_QUIZ_OPTIONS-1) distractors)
NUM_QUIZ_OPTIONS = 3  # Aim for 3 options (1 correct, 2 distractors)

def generate_quiz_question(user_id: int) -> Optional[Dict[str, Union[int, str, List[str]]]]:
    """
    Generates a quiz question for the user, prioritizing least tested words.

    Args:
        user_id: The ID of the user.

    Returns:
        A dictionary containing 'word_id' (int), 'word' (str), 'options' (List[str]), 
        and 'correct_definition_text' (str), or None if a quiz cannot be generated.
        The 'options' list is shuffled.
    """
    from src.database import get_least_tested_words, get_words_from_db # Function-scoped import

    logger.info(f"Attempting to generate quiz question for user_id {user_id}")
    
    all_user_word_objects = get_words_from_db(user_id, limit=200, offset=0, sort=False, get_objects=True)
    
    if not all_user_word_objects or len(all_user_word_objects) < MIN_WORDS_FOR_QUIZ:
        logger.warning(f"User {user_id} has insufficient words ({len(all_user_word_objects)}) in UserWords for a quiz (min: {MIN_WORDS_FOR_QUIZ}).")
        return None

    question_word_obj = None
    question_word_text = None
    correct_definition_text = None

    least_tested_word_ids = get_least_tested_words(user_id, count=max(5, NUM_QUIZ_OPTIONS * 2))
    
    if least_tested_word_ids:
        user_word_map = {obj['word_id']: obj['word'] for obj in all_user_word_objects}
        
        for word_id_candidate in least_tested_word_ids:
            if word_id_candidate in user_word_map:
                word_text_candidate = user_word_map[word_id_candidate]
                temp_def_text, _ = get_definition(word_text_candidate)
                if temp_def_text and "No definition found" not in temp_def_text and "Sorry, I couldn't fetch" not in temp_def_text:
                    question_word_obj = {'word_id': word_id_candidate, 'word': word_text_candidate}
                    question_word_text = word_text_candidate
                    correct_definition_text = temp_def_text
                    logger.info(f"Selected word '{question_word_text}' (ID: {word_id_candidate}) from least tested list for user {user_id}.")
                    break 
    
    if not question_word_obj:
        logger.info(f"No suitable word from least tested for user {user_id}, or list was empty. Falling back to random selection.")
        
        available_words_for_random_pick = list(all_user_word_objects) 
        random.shuffle(available_words_for_random_pick)

        for candidate_obj in available_words_for_random_pick:
            temp_def_text, _ = get_definition(candidate_obj['word'])
            if temp_def_text and "No definition found" not in temp_def_text and "Sorry, I couldn't fetch" not in temp_def_text:
                question_word_obj = candidate_obj
                question_word_text = candidate_obj['word']
                correct_definition_text = temp_def_text
                logger.info(f"Selected word '{question_word_text}' (ID: {question_word_obj['word_id']}) via random fallback for user {user_id}.")
                break 

    if not question_word_obj or not correct_definition_text:
        logger.error(f"Could not select any question word with a valid definition for user {user_id} after all fallbacks.")
        return None
            
    options = [correct_definition_text]
    
    distractor_pool = [w_obj for w_obj in all_user_word_objects if w_obj['word_id'] != question_word_obj['word_id']]
    random.shuffle(distractor_pool)

    num_distractors_needed = NUM_QUIZ_OPTIONS - 1
    distractors_added = 0

    for dist_obj in distractor_pool:
        if distractors_added >= num_distractors_needed:
            break
        
        distractor_def_text, _ = get_definition(dist_obj['word'])
        if distractor_def_text and \
           "No definition found" not in distractor_def_text and \
           "Sorry, I couldn't fetch" not in distractor_def_text and \
           distractor_def_text not in options: 
            options.append(distractor_def_text)
            distractors_added += 1
            logger.info(f"Added distractor: definition of '{dist_obj['word']}' for question_word '{question_word_text}' for user {user_id}")

    if len(options) < MIN_WORDS_FOR_QUIZ: 
        logger.warning(f"Could not generate enough unique options for word '{question_word_text}' for user {user_id}. Options count: {len(options)}. Need at least {MIN_WORDS_FOR_QUIZ}.")
        return None

    random.shuffle(options)

    logger.info(f"Successfully generated quiz for word '{question_word_text}' (ID: {question_word_obj['word_id']}) for user {user_id} with {len(options)} options.")
    return {
        "word_id": question_word_obj['word_id'], 
        "word": question_word_text,
        "options": options, 
        "correct_definition_text": correct_definition_text 
    }

def check_quiz_answer(word: str, selected_option_text: str, correct_definition_text: str) -> bool:
    logger.info(f"Checking quiz answer for word '{word}'. Selected: '{selected_option_text[:50]}...', Correct: '{correct_definition_text[:50]}...'")
    
    is_correct = (selected_option_text == correct_definition_text)
    
    if is_correct:
        logger.info(f"Answer for '{word}' is CORRECT.")
    else:
        logger.info(f"Answer for '{word}' is INCORRECT.")
    return is_correct
