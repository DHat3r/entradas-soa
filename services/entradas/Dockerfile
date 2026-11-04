# Se construye desde la raíz del repo porque necesita las librerías de libs/.
FROM python:3.14-slim

WORKDIR /srv
COPY libs/ libs/
COPY services/entradas/requirements.txt .
RUN pip install --no-cache-dir ./libs/mensajeria ./libs/basedatos -r requirements.txt

COPY services/entradas/app app/
COPY services/entradas/migraciones migraciones/
COPY services/entradas/alembic.ini .

USER nobody
# Las migraciones corren al arrancar para que docker compose up deje todo listo.
CMD ["sh", "-c", "alembic upgrade head && python -m app.main"]
