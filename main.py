import json
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# O3: Configuración básica de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# I8: Persistencia en archivo 
# Configuración de la ruta con pathlib 
BASE_DIR = Path(__file__).parent
DATOS_DIR = BASE_DIR / "datos"
ARCHIVO_LIBROS = DATOS_DIR / "libros.json"

# Función para cargar los libros al iniciar
def cargar_libros():
    if not ARCHIVO_LIBROS.exists():
        logger.info("El archivo de libros no existe, iniciando con lista vacía.") # (O3)
        return []
    try:
        with open(ARCHIVO_LIBROS, "r", encoding="utf-8") as f:
            contenido = f.read()
            if not contenido.strip() or json.loads(contenido) == []:
                logger.info("El archivo de libros está vacío, iniciando con lista vacía.") # (O3)
                return []
            logger.info(f"Libros cargados exitosamente desde {ARCHIVO_LIBROS}.") # (O3)
            return json.loads(contenido)
    except (json.JSONDecodeError, OSError):
        # Si el archivo está dañado o hay error, arranca vacía sin romperse (I8)
        logger.error("El archivo de libros está dañado, iniciando con lista vacía.") # (O3)
        return []

# Función para guardar los libros en el archivo después de cada cambio
def guardar_libros():
    DATOS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ARCHIVO_LIBROS, "w", encoding="utf-8") as f:
        json.dump(libros_db, f, ensure_ascii=False, indent=4)

# Inicializa la base de datos con lo que esté en el archivo
libros_db = cargar_libros()

# El siguiente id es el mayor guardado + 1 (o 1 si está vacía) (I8)
if libros_db:
    contador_id = max(libro["id"] for libro in libros_db) + 1
else:
    contador_id = 1

#  I1: Modelo Pydantic para validar los datos que llegan
class LibroEntrada(BaseModel):
    titulo: str = Field(..., min_length=3, max_length=100)
    autor: str = Field(..., min_length=3, max_length=60)
    anio: int = Field(..., ge=1000, le=2100)
    disponible: bool = True

# F1: GET en la raíz del sitio
@app.get("/")
def leer_raiz():
    """Devuelve el mensaje de bienvenida de la API.""" # (O5: Docstrings)
    return {"mensaje": "API de la biblioteca"}

# F2: GET para listar todos los libros
# I3: GET /libros con filtros opcionales de autor y disponibilidad
# I4: GET /libros con filtrado y paginación
@app.get("/libros")
def listar_libros(
    autor: str | None = None, 
    disponible: bool | None = None,
    desde: int | None = 0,
    limite: int | None = 100,
):
  """Devuelve la lista de libros, con filtros opcionales por autor y disponibilidad, y paginación.""" # (O5: Docstrings)
  resultado = libros_db

  # Filtra por autor (sin distinguir mayúsculas/minúsculas)
  if autor is not None:
    resultado = [
        libro for libro in resultado if libro["autor"].lower() == autor.lower()
    ]

  # Filtra por disponibilidad
  if disponible is not None:
    resultado = [
        libro for libro in resultado if libro["disponible"] == disponible
    ]
    
  # Aplica paginación (desde y límite)
  resultado = resultado[desde: desde + limite]

  return resultado

# F3: POST para crear un nuevo libro 
# I6: Conflicto 409
# I7: Ids que no se reutilizan
@app.post("/libros", status_code=201)
def crear_libro(libro: LibroEntrada):
  """Crea un nuevo libro y lo guarda en el archivo JSON.""" # (O5: Docstrings)
  global contador_id

  # Verifica si ya existe un libro con el mismo título y autor (sin importar mayúsculas/minúsculas)
  for libro_existente in libros_db:
    if (
        libro_existente["titulo"].lower() == libro.titulo.lower()
        and libro_existente["autor"].lower() == libro.autor.lower()
    ):
      raise HTTPException(
          status_code=409, detail="El libro ya existe con ese título y autor"
      )

  # Crea el diccionario poniendo primero el id y luego el resto de los campos
  nuevo_libro = {"id": contador_id, **libro.model_dump()}

  libros_db.append(nuevo_libro)
  contador_id += 1 # El contador avanza y nunca retrocede (I7)

  # Guarda los cambios en el archivo (I8)
  guardar_libros()
  logger.info(f"Nuevo libro creado con ID: {nuevo_libro['id']}") # (O3)
  return nuevo_libro

# I9: Búsqueda por texto en título o autor 
@app.get("/libros/buscar")
def buscar_libros(texto: str):
    """Busca libros por coincidencia de texto en el título o el autor, sin distinguir mayúsculas/minúsculas.""" # (O5: Docstrings)
    # Filtra los libros donde el texto esté en el título o en el autor 
    resultado = [
        libro for libro in libros_db
        if texto.lower() in libro["titulo"].lower() or texto.lower() in libro["autor"].lower()
    ]
    return resultado

# O2: Endpoint de estadísticas 
@app.get("/libros/estadisticas")
def obtener_estadisticas():
    """Devuelve el conteo de libros totales, disponibles y prestados.""" # (O5: Docstrings)
    total = len(libros_db)
    disponibles = sum(1 for libro in libros_db if libro["disponible"])
    prestados = total - disponibles
    
    return {
        "total": total,
        "disponibles": disponibles,
        "prestados": prestados
    }
 
# F4: GET /libros/{id} para buscar un libro por su id
# F5: si el id ingresado no es un número entero, devuelve 422
@app.get("/libros/{id}")
def obtener_libro_por_id(id: int):
  """Devuelve los detalles de un libro específico según su ID.""" # (O5: Docstrings)
  # Busca en nuestra lista si algún libro tiene el id que nos pasaron
  for libro in libros_db:
    if libro["id"] == id:
      return libro

  # Si el bucle termina y no lo encuentra, devuelve error 404 
  raise HTTPException(status_code=404, detail="Libro no encontrado")

# F6: DELETE /libros/{id} para borrar un libro por su id
@app.delete("/libros/{id}", status_code=204)
def borrar_libro(id: int):
    """Elimina un libro existente del catálogo según su ID.""" # (O5: Docstrings)
    # Busca el libro por su id en la lista
    for index, libro in enumerate(libros_db):
        if libro["id"] == id:
            # Si lo encuentra, lo elimina de la lista
            libros_db.pop(index)
      
            # Guarda los cambios en el archivo (I8)
            guardar_libros()
            logger.info(f"Libro con ID {id} eliminado correctamente.") # (O3)
            break
    else:
        # Si no se encuentra, devuelve 404 
        raise HTTPException(status_code=404, detail="Libro no encontrado")

# I2: PUT /libros/{id} para reemplazar un libro por completo
@app.put("/libros/{id}")
def actualizar_libro(id: int, libro_actualizado: LibroEntrada):
    """Reemplaza completamente los datos de un libro existente según su ID.""" # (O5: Docstrings)
    for index, libro in enumerate(libros_db):
        if libro["id"] == id:
            # Reemplaza los datos manteniendo el id original primero
            libro_modificado = {"id": id, **libro_actualizado.model_dump()}
            libros_db[index] = libro_modificado

            # Guarda los cambios en el archivo (I8)
            guardar_libros()
      
            return libro_modificado
    # Si no se encuentra el libro, devuelve 404
    raise HTTPException(status_code=404, detail="Libro no encontrado")

# Modelo para actualización parcial (todos los campos opcionales)
class LibroActualizacionParcial(BaseModel):
    titulo: str | None = Field(None, min_length=3, max_length=100)
    autor: str | None = Field(None, min_length=3, max_length=60)
    anio: int | None = Field(None, ge=1000, le=2100)
    disponible: bool | None = None

# I5: PATCH /libros/{id} para actualizar parcialmente un libro
@app.patch("/libros/{id}")
def actualizar_libro_parcial(id: int, libro_parcial: LibroActualizacionParcial):
    """Actualiza parcialmente los datos de un libro existente según su ID.""" # (O5: Docstrings)
    for index, libro in enumerate(libros_db):
        if libro["id"] == id:
            # Se obtiene sólo los campos que el usuario decidió enviar o cambiar
            datos_actualizados = libro_parcial.model_dump(exclude_unset=True)
            
            # Se actualizan únicamente esos campos en el diccionario del libro existente
            libro.update(datos_actualizados)

            # Guarda los cambios en el archivo (I8)
            guardar_libros()

            return libro
    # Si no se encuentra el libro, devuelve 404
    raise HTTPException(status_code=404, detail="Libro no encontrado")

# O1: Endpoint para prestar un libro
@app.post("/libros/{id}/prestar")
def prestar_libro(id: int):
    """Marca un libro disponible como prestado según su ID.""" # (O5: Docstrings)
    for libro in libros_db:
        if libro["id"] == id:
            # Si ya está prestado (false), devuelve conflicto 409
            if not libro["disponible"]:
                raise HTTPException(status_code=409, detail="El libro ya se encuentra prestado")
            
            # Se cambia el estado a prestado
            libro["disponible"] = False
            
            # O1 / I8: Guarda los cambios en el archivo
            guardar_libros()
            
            return libro
    # Si no se encuentra el libro, devuelve 404
    raise HTTPException(status_code=404, detail="Libro no encontrado")

# O1: Endpoint para devolver un libro
@app.post("/libros/{id}/devolver")
def devolver_libro(id: int):
    """Marca un libro prestado como disponible según su ID.""" # (O5: Docstrings)
    for libro in libros_db:
        if libro["id"] == id:
            # Si ya está disponible (true), devuelve conflicto 409
            if libro["disponible"]:
                raise HTTPException(status_code=409, detail="El libro ya se encuentra disponible")
            
            # Se cambia el estado a disponible
            libro["disponible"] = True
            
            # O1 / I8: Guarda los cambios en el archivo
            guardar_libros()
            
            return libro
    # Si no se encuentra el libro, devuelve 404
    raise HTTPException(status_code=404, detail="Libro no encontrado")