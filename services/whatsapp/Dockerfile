FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home gateway && mkdir -p /app/data && chown gateway:gateway /app/data
COPY __init__.py app.py run.py /app/services/whatsapp/
USER gateway
EXPOSE 8001
CMD ["python", "-m", "services.whatsapp.run", "--host", "0.0.0.0", "--port", "8001"]
