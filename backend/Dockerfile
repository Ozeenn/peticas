FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
COPY backend/requirements.lock.txt /app/backend/requirements.lock.txt
RUN pip install --no-cache-dir -r backend/requirements.lock.txt
COPY backend /app/backend
COPY public /app/public
COPY docs/MANUAL_MANUTENCAO.md docs/PRIVACIDADE_LGPD.md /app/docs/
RUN useradd --uid 10001 --create-home peticas
USER peticas
EXPOSE 4173
CMD ["python", "-m", "backend.run"]
