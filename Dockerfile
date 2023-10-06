WORKDIR /app

RUN apt-get update && apt-get install -y libpq-dev libpq5 gcc

COPY requirements.txt .

# Install the dependencies into a directory that we can easily copy in the next stage.
RUN pip install --no-cache-dir -r requirements.txt --target=/app

# Copy the rest of the code.
COPY ./bot.py .
COPY ./test_bot.py .
COPY ./database.py .


CMD ["python", "bot.py"]