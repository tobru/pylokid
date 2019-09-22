FROM python:3.7

# Install pdftotext
RUN set -x; \
    apt update && \
    apt install -y poppler-utils && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/pylokid
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD [ "python", "./main.py" ]
