# Se construye desde la raíz del repo porque necesita las librerías de libs/.
FROM python:3.14-slim

WORKDIR /srv
COPY libs/ libs/
COPY services/notificaciones/requirements.txt .
RUN pip install --no-cache-dir ./libs/mensajeria ./libs/basedatos -r requirements.txt

COPY services/notificaciones/app app/
COPY services/notificaciones/migraciones migraciones/
COPY services/notificaciones/alembic.ini .

USER nobody
# Las migraciones corren al arrancar para que docker compose up deje todo listo.
CMD ["sh", "-c", "alembic upgrade head && python -m app.main"]
