FROM python:3.9-slim

ARG TOKEN
ARG MERRIAM_WEBSTER_API_KEY

ARG TOKEN
ARG MERRIAM_WEBSTER_API_KEY

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install python-dotenv

# Install aiogram
RUN pip install aiogram

COPY . .

CMD ["python", "bot.py"]
