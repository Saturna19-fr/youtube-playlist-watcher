FROM python:3.12-slim


WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY playlist_watcher.py .

# State file lives here so it can be mounted as a volume
ENV STATE_DIR=/app/data
RUN mkdir -p ${STATE_DIR}

CMD ["python3", "-u", "playlist_watcher.py"]
