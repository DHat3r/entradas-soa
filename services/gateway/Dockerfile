# Se construye desde la raíz del repo porque necesita las librerías de libs/.
FROM python:3.14-slim

WORKDIR /srv
COPY libs/mensajeria libs/mensajeria/
COPY services/gateway/requirements.txt .
RUN pip install --no-cache-dir ./libs/mensajeria -r requirements.txt

COPY services/gateway/app app/

USER nobody
HEALTHCHECK --interval=5s --timeout=3s --retries=20 CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://localhost:8000/api/health')"]
# --proxy-headers: la IP real viene de nginx; el límite de login la necesita.
CMD ["uvicorn", "app.main:crear_app_de_produccion", "--factory", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
