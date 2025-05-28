# Use an official Python runtime as a parent image
FROM python:3.10-slim-bullseye

WORKDIR /app

RUN apt-get update && apt-get install -y libpq-dev libpq5 gcc

COPY requirements.txt .

# Install the dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code.
COPY src/ /app/src/
COPY commands/ /app/commands/
COPY main.py /app/
COPY test_bot.py /app/

CMD ["python", "main.py"]