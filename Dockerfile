FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py config.py init_demo_db.py ./

EXPOSE 8084

CMD ["python", "app.py"]
