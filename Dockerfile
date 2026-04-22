FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir -e .

ENV PORT=7860
ENV PYTHONIOENCODING=utf-8
EXPOSE 7860

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "7860"]
