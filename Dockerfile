FROM python:3.9-slim-bullseye

ARG TOKEN
ARG MERRIAM_WEBSTER_API_KEY

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install python-dotenv

COPY ./bot.py .
COPY ./test_bot.py .
COPY ./merriam_webster.py .

CMD ["python", "bot.py"]
