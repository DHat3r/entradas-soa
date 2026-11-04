# Se construye desde la raíz del repo porque necesita las librerías de libs/.
FROM python:3.14-slim

WORKDIR /srv
COPY libs/ libs/
COPY services/auth/requirements.txt .
RUN pip install --no-cache-dir ./libs/mensajeria ./libs/basedatos -r requirements.txt

COPY services/auth/app app/
COPY services/auth/migraciones migraciones/
COPY services/auth/alembic.ini .

USER nobody
# Las migraciones corren al arrancar para que docker compose up deje todo listo.
CMD ["sh", "-c", "alembic upgrade head && python -m app.main"]
