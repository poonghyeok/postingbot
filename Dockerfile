FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system postingbot \
    && adduser --system --ingroup postingbot postingbot

COPY requirements.txt ./
RUN pip install --no-cache-dir --requirement requirements.txt

COPY --chown=postingbot:postingbot bot.py ./

USER postingbot

CMD ["python", "bot.py"]
