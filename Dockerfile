# Usar una imagen base de Python
FROM python:3.9-slim

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar el archivo requirements.txt y luego instalar las dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el contenido del proyecto en el contenedor
COPY . .

# Exponer el puerto 8000 para el contenedor
EXPOSE 8000

# Comando de inicio para ejecutar la aplicación FastAPI con Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
