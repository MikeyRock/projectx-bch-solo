FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    flask==3.0.3 \
    flask-cors==4.0.1 \
    requests==2.32.3 \
    gunicorn==22.0.0

COPY app.py .

EXPOSE 3000

CMD ["gunicorn", "--bind", "0.0.0.0:3000", "--workers", "2", "--timeout", "30", "app:app"]
