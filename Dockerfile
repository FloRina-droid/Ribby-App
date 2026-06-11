FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV RIBBY_HOST=0.0.0.0
ENV RIBBY_DATA_DIR=/data/ribby_data

WORKDIR /app
COPY ribby_server.py ribby_app.html README.md ./

RUN mkdir -p /data/ribby_data
RUN python -m py_compile ribby_server.py
VOLUME ["/data"]
EXPOSE 7432

CMD ["python", "-u", "ribby_server.py"]
