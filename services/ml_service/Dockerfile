FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY train_model.py .
COPY ml_service.py .

RUN python train_model.py

EXPOSE 6000

CMD ["python", "ml_service.py"]