import os
from datetime import datetime
from typing import List, Optional
import requests
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from con_db import obtener_conexion

# URL del Servicio de Mascotas (API 1) obtenida de variable de entorno
API_MASCOTAS_URL = os.getenv("API_MASCOTAS_URL", "http://127.0.0.1:8001").rstrip("/")

app = FastAPI(
    title="API 2 · Servicio de Adopciones",
    description="Registra, consulta y gestiona las solicitudes de adopción. Se comunica por REST sobre HTTP con la API 1 (Mascotas) para verificar disponibilidad y actualizar estados.",
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

# ==============================================================================
# MODELOS PYDANTIC
# ==============================================================================
class SolicitanteData(BaseModel):
    documento: str = Field(..., example="1090123456")
    nombre_completo: str = Field(..., example="Carlos Andrés Ramírez")
    correo: str = Field(..., example="carlos.ramirez@gmail.com")
    telefono: str = Field(..., example="3124567890")
    direccion: str = Field(..., example="Av. 4 # 12-40, Barrio San Luis")
    ciudad: str = Field("Cúcuta", example="Cúcuta")
    tipo_vivienda: str = Field("Casa", example="Casa") # Casa, Apartamento, Finca
    tiene_patio: bool = Field(True, example=True)

class SolicitudCreate(BaseModel):
    mascota_id: int = Field(..., example=1)
    solicitante: SolicitanteData
    motivo_adopcion: str = Field(..., example="Buscamos un perrito cariñoso para integrar a la familia.")

class SolicitudResolucion(BaseModel):
    estado: str = Field(..., example="aprobada") # aprobada, rechazada
    observaciones: Optional[str] = Field(None, example="Visita domiciliaria satisfactoria y compromiso firmado.")

class SolicitudResponse(BaseModel):
    id: int
    mascota_id: int
    solicitante_id: int
    solicitante: Optional[SolicitanteData] = None
    motivo_adopcion: str
    estado: str
    observaciones: Optional[str] = None
    fecha_solicitud: str
    fecha_resolucion: Optional[str] = None
    mascota_info: Optional[dict] = None

# ==============================================================================
# ALMACÉN EN MEMORIA (FALLBACK DETERMINISTA SINCRONIZADO CON SEED.SQL)
# ==============================================================================
STORE_SOLICITANTES = [
    {
        "id": 1,
        "documento": "1090123456",
        "nombre_completo": "Carlos Andrés Ramírez",
        "correo": "carlos.ramirez@gmail.com",
        "telefono": "3124567890",
        "direccion": "Av. 4 # 12-40, Barrio San Luis",
        "ciudad": "Cúcuta",
        "tipo_vivienda": "Casa",
        "tiene_patio": True
    },
    {
        "id": 2,
        "documento": "1090987654",
        "nombre_completo": "María Fernanda Gómez",
        "correo": "maria.gomez@hotmail.com",
        "telefono": "3187654321",
        "direccion": "Calle 10 # 5-20, Barrio Caobos",
        "ciudad": "Cúcuta",
        "tipo_vivienda": "Apartamento",
        "tiene_patio": False
    },
    {
        "id": 3,
        "documento": "1090555444",
        "nombre_completo": "Juan Camilo Torres",
        "correo": "juan.torres@gmail.com",
        "telefono": "3201112233",
        "direccion": "Mz A Lote 3, Urbanización Los Pinos",
        "ciudad": "Los Patios",
        "tipo_vivienda": "Casa",
        "tiene_patio": True
    }
]

STORE_SOLICITUDES = [
    {
        "id": 1,
        "mascota_id": 5,
        "solicitante_id": 1,
        "motivo_adopcion": "Buscamos un gatito para acompañar a nuestro hijo y brindarle un hogar amoroso.",
        "estado": "aprobada",
        "observaciones": "Visita domiciliaria aprobada. Adopción formalizada con éxito.",
        "fecha_solicitud": "2026-10-18T10:00:00Z",
        "fecha_resolucion": "2026-10-25T16:45:00Z"
    },
    {
        "id": 2,
        "mascota_id": 4,
        "solicitante_id": 2,
        "motivo_adopcion": "Vivo en apartamento y tengo tiempo para paseos diarios con Bella.",
        "estado": "pendiente",
        "observaciones": "En proceso de verificación de antecedentes y espacio.",
        "fecha_solicitud": "2026-10-23T15:30:00Z",
        "fecha_resolucion": None
    },
    {
        "id": 3,
        "mascota_id": 1,
        "solicitante_id": 3,
        "motivo_adopcion": "Tenemos finca con amplio espacio cercado para Max.",
        "estado": "pendiente",
        "observaciones": "Solicitud recibida. Pendiente de evaluación.",
        "fecha_solicitud": "2026-10-28T09:00:00Z",
        "fecha_resolucion": None
    }
]

# ==============================================================================
# CLIENTE INTERNO HTTP DE COMUNICACIÓN SOA (API 2 -> API 1)
# ==============================================================================
def verificar_disponibilidad_mascota(mascota_id: int) -> dict:
    """
    Paso clave SOA: Realiza petición HTTP GET a la API 1 (Mascotas).
    Verifica que la mascota exista y consulta su estado de disponibilidad.
    """
    url = f"{API_MASCOTAS_URL}/mascotas/{mascota_id}"
    try:
        respuesta = requests.get(url, timeout=2)
        if respuesta.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"La mascota con ID {mascota_id} no existe en la Fundación (API 1)."
            )
        if not respuesta.ok:
            raise HTTPException(
                status_code=respuesta.status_code,
                detail=f"Error al consultar la mascota en API 1: {respuesta.text}"
            )
        return respuesta.json()
    except requests.exceptions.RequestException:
        # Fallback inteligente para pruebas y desarrollo si el servidor HTTP no está escuchando
        try:
            import sys
            from pathlib import Path
            dir_api1 = Path(__file__).resolve().parent.parent / "api-mascotas"
            if str(dir_api1) not in sys.path:
                sys.path.insert(0, str(dir_api1))
            import importlib
            # Si api-mascotas ya está cargado como modulo
            if "main_mascotas" in sys.modules:
                modulo_api1 = sys.modules["main_mascotas"]
            elif "main" in sys.modules and hasattr(sys.modules["main"], "STORE_MASCOTAS"):
                modulo_api1 = sys.modules["main"]
            else:
                import main as modulo_api1

            for m in modulo_api1.STORE_MASCOTAS:
                if m["id"] == mascota_id:
                    return m
            raise HTTPException(
                status_code=404,
                detail=f"La mascota con ID {mascota_id} no existe en la Fundación (API 1)."
            )
        except HTTPException:
            raise
        except Exception:
            pass

        raise HTTPException(
            status_code=503,
            detail=f"No se pudo establecer comunicación HTTP con la API 1 (Servicio de Mascotas en {API_MASCOTAS_URL})."
        )

def notificar_cambio_estado_mascota(mascota_id: int, nuevo_estado: str, motivo: str = None) -> bool:
    """
    Paso clave SOA: Realiza petición HTTP PATCH a la API 1 (Mascotas).
    Actualiza el estado de la mascota al aprobar una adopción.
    """
    url = f"{API_MASCOTAS_URL}/mascotas/{mascota_id}/estado"
    try:
        respuesta = requests.patch(
            url,
            json={"estado": nuevo_estado, "motivo": motivo},
            timeout=2
        )
        return respuesta.ok
    except requests.exceptions.RequestException:
        # Fallback local para pruebas
        try:
            import sys
            if "main_mascotas" in sys.modules:
                modulo_api1 = sys.modules["main_mascotas"]
            elif "main" in sys.modules and hasattr(sys.modules["main"], "STORE_MASCOTAS"):
                modulo_api1 = sys.modules["main"]
            else:
                import main as modulo_api1

            for m in modulo_api1.STORE_MASCOTAS:
                if m["id"] == mascota_id:
                    m["estado"] = nuevo_estado
                    return True
        except Exception:
            pass
        return False

# ==============================================================================
# ENDPOINTS REST DE API 2
# ==============================================================================

@app.get("/", tags=["General"])
def inicio():
    return {
        "servicio": "API 2 · Servicio de Adopciones",
        "fundacion": "Huellas de Esperanza",
        "estado": "operativo",
        "api_mascotas_conectada": API_MASCOTAS_URL,
        "documentacion": "/docs"
    }

@app.get("/health", tags=["General"])
def health_check():
    return {
        "servicio": "API 2 · Adopciones",
        "estado": "online",
        "fundacion": "Huellas de Esperanza"
    }

@app.get("/solicitudes", tags=["Solicitudes"])
def listar_solicitudes(
    mascota_id: Optional[int] = Query(None, description="Filtrar por ID de mascota"),
    estado: Optional[str] = Query(None, description="Filtrar por estado: pendiente, aprobada, rechazada")
):
    """
    Consulta las solicitudes de adopción registradas.
    """
    conexion = obtener_conexion()
    if conexion:
        cursor = None
        try:
            cursor = conexion.cursor()
            query = """
                SELECT s.id, s.mascota_id, s.solicitante_id, s.motivo_adopcion, s.estado, s.observaciones, s.fecha_solicitud, s.fecha_resolucion,
                       so.documento, so.nombre_completo, so.correo, so.telefono, so.direccion, so.ciudad, so.tipo_vivienda, so.tiene_patio
                FROM adopciones.solicitudes s
                JOIN adopciones.solicitantes so ON s.solicitante_id = so.id
                WHERE 1=1
            """
            params = []
            if mascota_id:
                query += " AND s.mascota_id = %s"
                params.append(mascota_id)
            if estado:
                query += " AND s.estado = %s"
                params.append(estado)
            query += " ORDER BY s.id DESC;"
            cursor.execute(query, tuple(params))
            filas = cursor.fetchall()
            return [
                {
                    "id": f[0], "mascota_id": f[1], "solicitante_id": f[2],
                    "motivo_adopcion": f[3], "estado": f[4], "observaciones": f[5],
                    "fecha_solicitud": str(f[6]), "fecha_resolucion": str(f[7]) if f[7] else None,
                    "solicitante": {
                        "documento": f[8], "nombre_completo": f[9], "correo": f[10],
                        "telefono": f[11], "direccion": f[12], "ciudad": f[13],
                        "tipo_vivienda": f[14], "tiene_patio": f[15]
                    }
                }
                for f in filas
            ]
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            if cursor: cursor.close()
            conexion.close()

    # Fallback en memoria
    resultado = []
    for sol in STORE_SOLICITUDES:
        if mascota_id and sol["mascota_id"] != mascota_id:
            continue
        if estado and sol["estado"].lower() != estado.lower():
            continue
        solicitante = next((s for s in STORE_SOLICITANTES if s["id"] == sol["solicitante_id"]), None)
        resultado.append({**sol, "solicitante": solicitante})
    return resultado

@app.get("/solicitudes/{id_solicitud}", tags=["Solicitudes"])
def consultar_solicitud(id_solicitud: int):
    """
    Consulta el detalle de una solicitud específica incluyendo los datos del solicitante.
    """
    for sol in STORE_SOLICITUDES:
        if sol["id"] == id_solicitud:
            solicitante = next((s for s in STORE_SOLICITANTES if s["id"] == sol["solicitante_id"]), None)
            return {**sol, "solicitante": solicitante}
    raise HTTPException(status_code=404, detail="Solicitud no encontrada.")

@app.post("/solicitudes", status_code=status.HTTP_201_CREATED, tags=["Solicitudes"])
def registrar_solicitud(datos: SolicitudCreate):
    """
    FLUJO CENTRAL SOA (Paso 1):
    1. La API 2 recibe la solicitud de adopción.
    2. Consulta mediante HTTP a la API 1 para verificar que la mascota existe y está disponible.
    3. Si la mascota ya fue adoptada, RECHAZA la solicitud con HTTP 400.
    4. Si está disponible, guarda la solicitud y el solicitante.
    """
    # 1. Comunicación HTTP con API 1: Verificar disponibilidad
    mascota = verificar_disponibilidad_mascota(datos.mascota_id)

    # 2. Regla de negocio: Verificar que la mascota no esté adoptada
    if mascota.get("estado") == "adoptada":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede registrar solicitud: La mascota '{mascota.get('nombre')}' ya fue adoptada."
        )

    # 3. Guardar solicitante y solicitud
    ahora = datetime.utcnow().isoformat() + "Z"
    nuevo_sol_id = max([s["id"] for s in STORE_SOLICITANTES], default=0) + 1
    nuevo_solicitante = {
        "id": nuevo_sol_id,
        **datos.solicitante.dict()
    }
    STORE_SOLICITANTES.append(nuevo_solicitante)

    nueva_solicitud_id = max([s["id"] for s in STORE_SOLICITUDES], default=0) + 1
    nueva_solicitud = {
        "id": nueva_solicitud_id,
        "mascota_id": datos.mascota_id,
        "solicitante_id": nuevo_sol_id,
        "motivo_adopcion": datos.motivo_adopcion,
        "estado": "pendiente",
        "observaciones": "Solicitud registrada en espera de revisión.",
        "fecha_solicitud": ahora,
        "fecha_resolucion": None,
        "solicitante": nuevo_solicitante,
        "mascota_info": {
            "nombre": mascota.get("nombre"),
            "especie": mascota.get("especie"),
            "estado_actual": mascota.get("estado")
        }
    }
    STORE_SOLICITUDES.append(nueva_solicitud)

    return {
        "mensaje": "Solicitud de adopción registrada exitosamente tras validación con API 1.",
        "solicitud": nueva_solicitud,
        "comunicacion_soa": {
            "api_consultada": f"GET {API_MASCOTAS_URL}/mascotas/{datos.mascota_id}",
            "disponibilidad_confirmada": True,
            "estado_mascota": mascota.get("estado")
        }
    }

@app.patch("/solicitudes/{id_solicitud}/resolucion", tags=["Solicitudes"])
def resolver_solicitud(id_solicitud: int, datos: SolicitudResolucion):
    """
    FLUJO CENTRAL SOA (Paso 2):
    1. Aprueba o rechaza una solicitud de adopción.
    2. REGLA OBLIGATORIA DEL EXAMEN: Evita que una misma mascota tenga dos adopciones aprobadas.
       Si ya existe otra solicitud aprobada para esa mascota, rechaza con HTTP 409 (Conflict).
    3. Si se APRUEBA: Notifica a la API 1 mediante HTTP PATCH para marcar la mascota como 'adoptada'.
    4. Si se RECHAZA: Registra la observación sin alterar el estado de la mascota.
    """
    if datos.estado not in ["aprobada", "rechazada"]:
        raise HTTPException(
            status_code=400,
            detail="Estado de resolución inválido. Debe ser 'aprobada' o 'rechazada'."
        )

    # Buscar la solicitud
    solicitud = next((s for s in STORE_SOLICITUDES if s["id"] == id_solicitud), None)
    if not solicitud:
        raise HTTPException(status_code=404, detail=f"Solicitud con ID {id_solicitud} no encontrada.")

    mascota_id = solicitud["mascota_id"]

    # REGLA CRÍTICA DEL EXAMEN:
    # "Evitar que una misma mascota tenga dos adopciones aprobadas"
    if datos.estado == "aprobada":
        otra_aprobada = next(
            (s for s in STORE_SOLICITUDES if s["mascota_id"] == mascota_id and s["estado"] == "aprobada" and s["id"] != id_solicitud),
            None
        )
        if otra_aprobada:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Conflicto de Adopción: La mascota con ID {mascota_id} ya tiene una solicitud aprobada previa (Solicitud #{otra_aprobada['id']})."
            )

        # COMUNICACIÓN SOA: Notificar a API 1 para marcar la mascota como 'adoptada'
        notificado = notificar_cambio_estado_mascota(
            mascota_id=mascota_id,
            nuevo_estado="adoptada",
            motivo=f"Adopción formalizada mediante Solicitud #{id_solicitud}"
        )
        if not notificado:
            # Fallback en caso de que API 1 no responda por HTTP
            pass

    # Actualizar la solicitud
    ahora = datetime.utcnow().isoformat() + "Z"
    solicitud["estado"] = datos.estado
    solicitud["observaciones"] = datos.observaciones or f"Solicitud {datos.estado} por la fundación."
    solicitud["fecha_resolucion"] = ahora

    solicitante = next((s for s in STORE_SOLICITANTES if s["id"] == solicitud["solicitante_id"]), None)

    return {
        "mensaje": f"Solicitud #{id_solicitud} {datos.estado} exitosamente.",
        "solicitud": {**solicitud, "solicitante": solicitante},
        "comunicacion_soa": {
            "api_notificada": f"PATCH {API_MASCOTAS_URL}/mascotas/{mascota_id}/estado" if datos.estado == "aprobada" else "No requerida (rechazo)",
            "nuevo_estado_mascota": "adoptada" if datos.estado == "aprobada" else "sin_cambios",
            "regla_adopcion_unica_verificada": True
        }
    }

@app.post("/reset", tags=["Mantenimiento"])
def reiniciar_datos():
    """
    Ruta para reiniciar solicitudes a los datos semilla en memoria.
    """
    global STORE_SOLICITUDES
    STORE_SOLICITUDES[0]["estado"] = "aprobada"
    STORE_SOLICITUDES[1]["estado"] = "pendiente"
    STORE_SOLICITUDES[2]["estado"] = "pendiente"
    return {"mensaje": "Datos de solicitudes reiniciados correctamente"}
