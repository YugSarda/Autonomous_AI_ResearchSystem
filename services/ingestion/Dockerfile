FROM python:3.11-slim

WORKDIR /app

COPY services/ingestion/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Extra deps in a separate layer so changes here don't reinstall the big stack
COPY services/ingestion/requirements-extra.txt .
RUN pip install --no-cache-dir -r requirements-extra.txt

COPY services/ingestion/ .
COPY shared/ ./shared/

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]