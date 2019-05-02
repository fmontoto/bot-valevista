FROM python:3.6.4-slim

RUN mkdir /home/valevista

COPY requirements.txt /tmp/bot_requirements.txt

RUN pip install --upgrade pip && pip install -r /tmp/bot_requirements.txt

WORKDIR /home/valevista

CMD ["python", "-m", "src.bot"] 
