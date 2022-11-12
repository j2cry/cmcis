FROM python:3.9-slim
LABEL maintainer="fragarie"
LABEL description="CMCIS telegram bot"

RUN apt-get update \
  && apt-get install -y --no-install-recommends gettext \
  && apt-get autoremove -yqq --purge \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

RUN useradd -ms /bin/bash bot
RUN python3 -m venv /home/bot/venv
COPY requirements.txt /home/bot
RUN /home/bot/venv/bin/pip3 install -r /home/bot/requirements.txt
COPY . /home/bot/
WORKDIR /home/bot

USER bot
ENTRYPOINT ["/home/bot/venv/bin/python3", "bot.py"]
