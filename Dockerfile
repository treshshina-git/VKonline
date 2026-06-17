FROM python:3.11-slim

WORKDIR /app

COPY . ./

ENV PYTHONUNBUFFERED=1

# Long polling
CMD ["python", "-m", "src.main"]

