FROM docker.io/python:3.9 AS base

# Install pdftotext
RUN set -x; \
    apt update && \
    apt install -y poppler-utils && \
    rm -rf /var/lib/apt/lists/*

ENV HOME=/app

WORKDIR ${HOME}

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

FROM builder AS installer

COPY --from=builder \
      /app/dist /app/dist
RUN pip install /app/dist/pylokid-*-py3-none-any.whl

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
