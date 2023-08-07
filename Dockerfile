# First stage: build
FROM python:3.9-slim-bullseye as builder

WORKDIR /app

COPY requirements.txt .
# Install the dependencies into a directory that we can easily copy in the next stage.
RUN pip install --no-cache-dir -r requirements.txt --target=/app

# Second stage: run
FROM python:3.9-slim-bullseye

WORKDIR /app

# Copy the installed dependencies from the first stage.
COPY --from=builder /app /app

# Copy the rest of the code.
# COPY ./bot.py .
# COPY ./test_bot.py .
# COPY ./utils .  # Add this line to copy the utils directory

COPY . .

CMD ["python", "bot.py"]