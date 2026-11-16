FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY ai-service/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY contracts/ ./contracts/
COPY ai-service/wonit_ai/ ./wonit_ai/
USER 10001:10001
CMD ["python", "-m", "wonit_ai.worker"]
