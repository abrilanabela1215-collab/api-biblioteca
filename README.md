# API Biblioteca - FastAPI

Sistema de gestión de biblioteca desarrollado con FastAPI, Pydantic y persistencia en archivos JSON.

## Requisitos
- Python 3.10+
- FastAPI
- Uvicorn
- Pydantic
- Ruff

## Instalación y Ejecución

1. Crear y activar el entorno virtual: # En Windows
   python -m venv .venv
   .venv\Scripts\Activate  

2. Instalar las dependencias con pip:
    pip install -r requirements.txt

3. Ejecutar el servidor con Uvicorn:
    uvicorn main:app --reload

4. Abrir la documentación interactiva en el navegador:

Swagger UI: http://127.0.0.1:8000/docs