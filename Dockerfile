FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV RIBBY_HOST=0.0.0.0
ENV RIBBY_DATA_DIR=/data/ribby_data

WORKDIR /app
COPY ribby_server.py ribby_app.html README.md ./
COPY ribby_data_seed ./ribby_data_seed

RUN mkdir -p /data/ribby_data && chmod -R 777 /data
RUN python -m py_compile ribby_server.py
VOLUME ["/data"]
EXPOSE 7432

CMD ["sh", "-c", "echo '=== Ribby container start ==='; pwd; ls -la; python -V; env | sort | grep -E '^(PORT|RIBBY_)=' || true; exec python -u ribby_server.py"]
