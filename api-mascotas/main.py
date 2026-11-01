import os
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from con_db import obtener_conexion

app = FastAPI(
    title="API 1 · Servicio de Mascotas",
    description="Administra el registro, consulta y disponibilidad de las mascotas de la Fundación Huellas de Esperanza.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse

@app.get("/mascotas/docs", include_in_schema=False)
def swagger_ui_mascotas():
    return get_swagger_ui_html(openapi_url="/mascotas/openapi.json", title="API 1 · Mascotas - Swagger UI")

@app.get("/mascotas/openapi.json", include_in_schema=False)
def openapi_mascotas():
    return JSONResponse(app.openapi())


# ==============================================================================
# MODELOS PYDANTIC
# ==============================================================================
class MascotaBase(BaseModel):
    nombre: str = Field(..., example="Max")
    especie: str = Field(..., example="Perro") # Perro, Gato, Otro
    raza: str = Field("Mestizo", example="Golden Retriever Mestizo")
    edad_meses: int = Field(..., ge=0, example=24)
    sexo: str = Field(..., example="Macho") # Macho, Hembra
    tamano: str = Field(..., example="Grande") # Pequeno, Mediano, Grande
    descripcion: Optional[str] = Field(None, example="Juguetón, sociable y cariñoso")
    foto_url: Optional[str] = Field(None, example="https://images.unsplash.com/photo-1552053831-71594a27632d")

class MascotaCreate(MascotaBase):
    pass

class MascotaUpdateEstado(BaseModel):
    estado: str = Field(..., example="adoptada") # disponible, en_proceso, adoptada
    motivo: Optional[str] = Field(None, example="Adopción formalizada con éxito")

class MascotaResponse(MascotaBase):
    id: int
    estado: str
    fecha_ingreso: str
    fecha_actualizacion: str

# ==============================================================================
# ALMACÉN EN MEMORIA (FALLBACK DETERMINISTA SINCRONIZADO CON SEED.SQL)
# ==============================================================================
STORE_MASCOTAS = [
    {
        "id": 1,
        "nombre": "Max",
        "especie": "Perro",
        "raza": "Golden Retriever Mestizo",
        "edad_meses": 24,
        "sexo": "Macho",
        "tamano": "Grande",
        "descripcion": "Juguetón, sociable con niños y otros perros. Vacunado y esterilizado.",
        "foto_url": "https://images.unsplash.com/photo-1552053831-71594a27632d?auto=format&fit=crop&w=600&q=80",
        "estado": "disponible",
        "fecha_ingreso": "2026-10-15T10:00:00Z",
        "fecha_actualizacion": "2026-10-15T10:00:00Z"
    },
    {
        "id": 2,
        "nombre": "Luna",
        "especie": "Gato",
        "raza": "Siamés Mestizo",
        "edad_meses": 12,
        "sexo": "Hembra",
        "tamano": "Pequeno",
        "descripcion": "Tranquila, cariñosa y ronroneadora. Ideal para apartamento.",
        "foto_url": "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?auto=format&fit=crop&w=600&q=80",
        "estado": "disponible",
        "fecha_ingreso": "2026-10-18T14:30:00Z",
        "fecha_actualizacion": "2026-10-18T14:30:00Z"
    },
    {
        "id": 3,
        "nombre": "Rocky",
        "especie": "Perro",
        "raza": "Criollo / Labrador",
        "edad_meses": 36,
        "sexo": "Macho",
        "tamano": "Mediano",
        "descripcion": "Excelente compañero de caminatas, muy obediente y leal.",
        "foto_url": "https://images.unsplash.com/photo-1543466835-00a7907e9de1?auto=format&fit=crop&w=600&q=80",
        "estado": "disponible",
        "fecha_ingreso": "2026-10-20T09:15:00Z",
        "fecha_actualizacion": "2026-10-20T09:15:00Z"
    },
    {
        "id": 4,
        "nombre": "Bella",
        "especie": "Perro",
        "raza": "Poodle Mestizo",
        "edad_meses": 8,
        "sexo": "Hembra",
        "tamano": "Pequeno",
        "descripcion": "Cachorrita activa y dulce, rescatada de la zona céntrica.",
        "foto_url": "https://images.unsplash.com/photo-1583511655857-d19b40a7a54e?auto=format&fit=crop&w=600&q=80",
        "estado": "en_proceso",
        "fecha_ingreso": "2026-10-22T11:00:00Z",
        "fecha_actualizacion": "2026-10-22T11:00:00Z"
    },
    {
        "id": 5,
        "nombre": "Milo",
        "especie": "Gato",
        "raza": "Común Europeo",
        "edad_meses": 18,
        "sexo": "Macho",
        "tamano": "Mediano",
        "descripcion": "Curioso, limpio y muy juguetón. Ya fue adoptado por una hermosa familia.",
        "foto_url": "https://images.unsplash.com/photo-1573865526739-10659fec78a5?auto=format&fit=crop&w=600&q=80",
        "estado": "adoptada",
        "fecha_ingreso": "2026-10-10T08:00:00Z",
        "fecha_actualizacion": "2026-10-25T16:45:00Z"
    }
]

# ==============================================================================
# ENDPOINTS REST DE API 1
# ==============================================================================

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(STATIC_DIR):
    css_dir = os.path.join(STATIC_DIR, "css")
    js_dir = os.path.join(STATIC_DIR, "js")
    if os.path.exists(css_dir):
        app.mount("/css", StaticFiles(directory=css_dir), name="css")
    if os.path.exists(js_dir):
        app.mount("/js", StaticFiles(directory=js_dir), name="js")

@app.get("/", tags=["General"])
def inicio():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {
        "servicio": "API 1 · Servicio de Mascotas",
        "fundacion": "Huellas de Esperanza",
        "estado": "operativo",
        "documentacion": "/docs"
    }

@app.get("/health", tags=["General"])
def health_check():
    return {
        "servicio": "API 1 · Mascotas",
        "estado": "online",
        "fundacion": "Huellas de Esperanza"
    }



@app.get("/mascotas", response_model=List[MascotaResponse], tags=["Mascotas"])
def listar_mascotas(
    estado: Optional[str] = Query(None, description="Filtrar por estado: disponible, en_proceso, adoptada"),
    especie: Optional[str] = Query(None, description="Filtrar por especie: Perro, Gato")
):
    """
    Consulta el catálogo de mascotas disponibles o registradas en la fundación.
    """
    conexion = obtener_conexion()
    if conexion:
        cursor = None
        try:
            cursor = conexion.cursor()
            query = "SELECT id, nombre, especie, raza, edad_meses, sexo, tamano, descripcion, foto_url, estado, fecha_ingreso, fecha_actualizacion FROM mascotas.mascotas WHERE 1=1"
            params = []
            if estado:
                query += " AND estado = %s"
                params.append(estado)
            if especie:
                query += " AND especie = %s"
                params.append(especie)
            query += " ORDER BY id ASC;"
            cursor.execute(query, tuple(params))
            filas = cursor.fetchall()
            return [
                {
                    "id": f[0], "nombre": f[1], "especie": f[2], "raza": f[3],
                    "edad_meses": f[4], "sexo": f[5], "tamano": f[6],
                    "descripcion": f[7], "foto_url": f[8], "estado": f[9],
                    "fecha_ingreso": str(f[10]), "fecha_actualizacion": str(f[11])
                }
                for f in filas
            ]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error consultando base de datos: {e}")
        finally:
            if cursor: cursor.close()
            conexion.close()

    # Fallback en memoria
    resultado = STORE_MASCOTAS
    if estado:
        resultado = [m for m in resultado if m["estado"].lower() == estado.lower()]
    if especie:
        resultado = [m for m in resultado if m["especie"].lower() == especie.lower()]
    return resultado

@app.get("/mascotas/{id_mascota}", response_model=MascotaResponse, tags=["Mascotas"])
def consultar_mascota(id_mascota: int):
    """
    Consulta el detalle de una mascota.
    Punto clave de integración: utilizado por la API 2 (Adopciones) para verificar disponibilidad.
    """
    conexion = obtener_conexion()
    if conexion:
        cursor = None
        try:
            cursor = conexion.cursor()
            cursor.execute(
                """
                SELECT id, nombre, especie, raza, edad_meses, sexo, tamano, descripcion, foto_url, estado, fecha_ingreso, fecha_actualizacion
                FROM mascotas.mascotas
                WHERE id = %s;
                """,
                (id_mascota,)
            )
            f = cursor.fetchone()
            if not f:
                raise HTTPException(status_code=404, detail=f"Mascota con ID {id_mascota} no encontrada.")
            return {
                "id": f[0], "nombre": f[1], "especie": f[2], "raza": f[3],
                "edad_meses": f[4], "sexo": f[5], "tamano": f[6],
                "descripcion": f[7], "foto_url": f[8], "estado": f[9],
                "fecha_ingreso": str(f[10]), "fecha_actualizacion": str(f[11])
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            if cursor: cursor.close()
            conexion.close()

    # Fallback en memoria
    for m in STORE_MASCOTAS:
        if m["id"] == id_mascota:
            return m
    raise HTTPException(status_code=404, detail=f"Mascota con ID {id_mascota} no encontrada.")

@app.post("/mascotas", response_model=MascotaResponse, status_code=status.HTTP_201_CREATED, tags=["Mascotas"])
def registrar_mascota(datos: MascotaCreate):
    """
    Registra una nueva mascota en la fundación.
    """
    ahora = datetime.utcnow().isoformat() + "Z"
    conexion = obtener_conexion()
    if conexion:
        cursor = None
        try:
            cursor = conexion.cursor()
            cursor.execute(
                """
                INSERT INTO mascotas.mascotas (
                    nombre, especie, raza, edad_meses, sexo, tamano, descripcion, foto_url, estado
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'disponible')
                RETURNING id, fecha_ingreso, fecha_actualizacion;
                """,
                (
                    datos.nombre, datos.especie, datos.raza, datos.edad_meses,
                    datos.sexo, datos.tamano, datos.descripcion, datos.foto_url
                )
            )
            res = cursor.fetchone()
            conexion.commit()
            return {
                **datos.dict(),
                "id": res[0],
                "estado": "disponible",
                "fecha_ingreso": str(res[1]),
                "fecha_actualizacion": str(res[2])
            }
        except Exception as e:
            if conexion: conexion.rollback()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            if cursor: cursor.close()
            conexion.close()

    # Fallback en memoria
    nuevo_id = max([m["id"] for m in STORE_MASCOTAS], default=0) + 1
    nueva = {
        **datos.dict(),
        "id": nuevo_id,
        "estado": "disponible",
        "fecha_ingreso": ahora,
        "fecha_actualizacion": ahora
    }
    STORE_MASCOTAS.append(nueva)
    return nueva

@app.patch("/mascotas/{id_mascota}/estado", response_model=MascotaResponse, tags=["Mascotas"])
def actualizar_estado_mascota(id_mascota: int, datos: MascotaUpdateEstado):
    """
    Actualiza el estado de disponibilidad de la mascota ('disponible', 'en_proceso', 'adoptada').
    Punto clave de integración: invocado por la API 2 (Adopciones) al aprobar o resolver una solicitud.
    """
    estados_validos = ["disponible", "en_proceso", "adoptada"]
    if datos.estado not in estados_validos:
        raise HTTPException(
            status_code=400,
            detail=f"Estado inválido. Opciones permitidas: {', '.join(estados_validos)}"
        )

    ahora = datetime.utcnow().isoformat() + "Z"
    conexion = obtener_conexion()
    if conexion:
        cursor = None
        try:
            cursor = conexion.cursor()
            cursor.execute(
                """
                UPDATE mascotas.mascotas
                SET estado = %s, fecha_actualizacion = now()
                WHERE id = %s
                RETURNING id, nombre, especie, raza, edad_meses, sexo, tamano, descripcion, foto_url, estado, fecha_ingreso, fecha_actualizacion;
                """,
                (datos.estado, id_mascota)
            )
            f = cursor.fetchone()
            if not f:
                raise HTTPException(status_code=404, detail=f"Mascota con ID {id_mascota} no encontrada.")
            conexion.commit()
            return {
                "id": f[0], "nombre": f[1], "especie": f[2], "raza": f[3],
                "edad_meses": f[4], "sexo": f[5], "tamano": f[6],
                "descripcion": f[7], "foto_url": f[8], "estado": f[9],
                "fecha_ingreso": str(f[10]), "fecha_actualizacion": str(f[11])
            }
        except HTTPException:
            raise
        except Exception as e:
            if conexion: conexion.rollback()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            if cursor: cursor.close()
            conexion.close()

    # Fallback en memoria
    for m in STORE_MASCOTAS:
        if m["id"] == id_mascota:
            m["estado"] = datos.estado
            m["fecha_actualizacion"] = ahora
            return m
    raise HTTPException(status_code=404, detail=f"Mascota con ID {id_mascota} no encontrada.")

@app.post("/reset", tags=["Mantenimiento"])
def reiniciar_datos():
    """
    Ruta para reiniciar los datos de demostración en memoria.
    """
    global STORE_MASCOTAS
    # Reinicia a los valores iniciales
    STORE_MASCOTAS[0]["estado"] = "disponible"
    STORE_MASCOTAS[1]["estado"] = "disponible"
    STORE_MASCOTAS[2]["estado"] = "disponible"
    STORE_MASCOTAS[3]["estado"] = "en_proceso"
    STORE_MASCOTAS[4]["estado"] = "adoptada"
    return {"mensaje": "Datos de mascotas reiniciados correctamente"}
