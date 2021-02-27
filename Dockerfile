## ----------- Step 1
FROM docker.io/python:3.9 AS base

# Install pdftotext
RUN set -x; \
    apt update && \
    apt install -y poppler-utils && \
    rm -rf /var/lib/apt/lists/*

ENV HOME=/app

WORKDIR ${HOME}

## ----------- Step 2
FROM base AS builder

ENV PATH=${PATH}:${HOME}/.poetry/bin

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      curl \
 && rm -rf /var/lib/apt/lists/* \
 && curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python - --version 1.1.0 \
 && mkdir -p /app/.config

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false \
 && poetry install --no-dev --no-root

COPY . ./

RUN poetry build --format wheel

## ----------- Step 3
FROM builder AS installer

COPY --from=builder \
      /app/dist /app/dist
RUN pip install /app/dist/pylokid-*-py3-none-any.whl

COPY hack/patches/*.patch /tmp/

# The ugliest possible way to workaround https://github.com/MechanicalSoup/MechanicalSoup/issues/356
# For some unknown reasons Lodur now wants "Content-Type: application/pdf" set in the multipart
# data section. And as I couln't figure out yet how to do that in MechanicalSoup and I only upload PDFs
# I just patch it to hardcode it. YOLO
RUN \
  patch -p0 /usr/local/lib/python3.9/site-packages/mechanicalsoup/browser.py < /tmp/mechsoup-browser-content-type.patch && \
  patch -p0 /usr/local/lib/python3.9/site-packages/mechanicalsoup/stateful_browser.py < /tmp/mechsoup-link-regex.patch

## ----------- Step 4
FROM base AS runtime

COPY --from=installer \
      /usr/local/lib/python3.9/site-packages/ /usr/local/lib/python3.9/site-packages/
COPY --from=installer \
      /usr/local/bin/* \
      /usr/local/bin/

RUN chgrp 0 /app/ \
 && chmod g+rwX /app/

USER 1001

CMD [ "pylokid" ]
