# syntax=docker/dockerfile:1
FROM --platform=$BUILDPLATFORM python:3.11-bookworm AS exporter
RUN pip install "poetry<2"
RUN poetry self add poetry-plugin-export
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1
WORKDIR /export
COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt --output requirements.txt

FROM python:3.11-slim-bookworm AS runtime
WORKDIR /app
COPY --from=exporter /export/requirements.txt ./
RUN pip install -r ./requirements.txt
COPY edp2mqtt ./edp2mqtt

EXPOSE 50000/udp

ENTRYPOINT ["python", "-m", "edp2mqtt.main"]
