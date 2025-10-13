ARG BUILD_FROM=ghcr.io/hassio-addons/base:17.2.5
FROM $BUILD_FROM

ENV LANG C.UTF-8

RUN apk add --no-cache ca-certificates nginx python3 py3-requests py3-flask

WORKDIR /app
COPY backend.py /app/backend.py
COPY www/ /app/www/
COPY nginx.conf /etc/nginx/nginx.conf

COPY services/nginx/run /etc/services.d/nginx/run
COPY services/backend/run /etc/services.d/backend/run