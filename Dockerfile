FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV RIBBY_HOST=0.0.0.0
ENV RIBBY_DATA_DIR=/data/ribby_data

WORKDIR /app
COPY ribby_server.py ribby_images.py ribby_app.html prepare_image_references.py ./
COPY THIRD_PARTY_NOTICES.md ./
COPY licenses/ ./licenses/
COPY ribby_data_seed.zip.part* ./
COPY ribby_image_seed.zip.part* ribby_image_seed.zip.manifest.json ./

RUN mkdir -p /data/ribby_data && chmod -R 777 /data
RUN python -m py_compile ribby_server.py ribby_images.py prepare_image_references.py
VOLUME ["/data"]
EXPOSE 7432

CMD ["sh", "-c", "echo '=== Ribby container start ==='; pwd; ls -la; python -V; env | sort | grep -E '^(PORT|RIBBY_)=' || true; exec python -u ribby_server.py"]
