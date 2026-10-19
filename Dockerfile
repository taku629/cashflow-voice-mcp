FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir .
ENV HOST=0.0.0.0 PORT=8000 CASHFLOW_DB=/tmp/cashflow.db
EXPOSE 8000
CMD ["cashflow-voice"]
