FROM python:3.9-alpine

WORKDIR /app

COPY . .

RUN python3 -m pip install -U discord.py
RUN python3 -m pip install python-dotenv

CMD ["python3", "goose_bot.py"]