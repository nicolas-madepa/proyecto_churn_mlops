# Imagen base de Python (variante slim para una imagen más liviana)
FROM python:3.12-slim

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Buenas prácticas: sin .pyc y logs sin buffer
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copiar e instalar dependencias primero (aprovecha la caché de capas de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el resto del proyecto
COPY . .

# Puerto en el que escucha la API dentro del contenedor
EXPOSE 8000

# Verificación de salud: Docker consulta /health periódicamente para marcar el
# contenedor como healthy/unhealthy (variación técnica del Lab 4).
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Comando para iniciar el servicio
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
