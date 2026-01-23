FROM python:3.12-slim


# # Evita archivos .pyc y buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# # Directorio de trabajo
WORKDIR /BuzzySocket

# # Copiamos requirements primero (mejor cache)
COPY requeriments.txt .

# Instalamos dependencias
RUN pip install --upgrade pip \
    && pip install -r requeriments.txt

# Copiamos el proyecto
COPY . .

# Exponemos el puerto
EXPOSE 8001

# Comando final (SOLO aquí se corre la app)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
