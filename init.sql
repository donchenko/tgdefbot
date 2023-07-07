CREATE DATABASE tgdefbot;

\c tgdefbot;

CREATE TABLE Users (
    user_id INT PRIMARY KEY,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255)
);

CREATE TABLE Words (
    word_id SERIAL PRIMARY KEY,
    word VARCHAR(255) NOT NULL,
    part_of_speech VARCHAR(255),
    definition TEXT,
    example TEXT,
    pronunciation VARCHAR(255),
    audio_link VARCHAR(255)
);

CREATE TABLE UserWords (
    user_id INT,
    word_id INT,
    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (word_id) REFERENCES Words(word_id),
    PRIMARY KEY (user_id, word_id)
);
