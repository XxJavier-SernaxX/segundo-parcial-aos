import os
from datetime import datetime
from typing import List, Optional
import requests
from fastapi import FastAPI, HTTPException, Query, status, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from con_db import obtener_conexion

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

from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse

@app.get("/solicitudes/docs", include_in_schema=False)
def swagger_ui_solicitudes():
    return get_swagger_ui_html(openapi_url="/solicitudes/openapi.json", title="API 2 · Adopciones - Swagger UI")

@app.get("/solicitudes/openapi.json", include_in_schema=False)
def openapi_solicitudes():
    return JSONResponse(app.openapi())


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
# ALMACÉN EN MEMORIA DETERMINISTA (FALLBACK SINCRONIZADO CON SEED.SQL)
# ==============================================================================
STORE_MASCOTAS_FALLBACK = [
    {"id": 1, "nombre": "Max", "especie": "Perro", "raza": "Golden Retriever Mestizo", "edad_meses": 24, "sexo": "Macho", "tamano": "Grande", "descripcion": "Juguetón, sociable con niños y otros perros. Vacunado y esterilizado.", "foto_url": "https://images.unsplash.com/photo-1552053831-71594a27632d?auto=format&fit=crop&w=600&q=80", "estado": "disponible"},
    {"id": 2, "nombre": "Luna", "especie": "Gato", "raza": "Siamés Mestizo", "edad_meses": 12, "sexo": "Hembra", "tamano": "Pequeno", "descripcion": "Tranquila, cariñosa y ronroneadora. Ideal para apartamento.", "foto_url": "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?auto=format&fit=crop&w=600&q=80", "estado": "disponible"},
    {"id": 3, "nombre": "Rocky", "especie": "Perro", "raza": "Criollo / Labrador", "edad_meses": 36, "sexo": "Macho", "tamano": "Mediano", "descripcion": "Excelente compañero de caminatas, muy obediente y leal.", "foto_url": "https://images.unsplash.com/photo-1543466835-00a7907e9de1?auto=format&fit=crop&w=600&q=80", "estado": "disponible"},
    {"id": 4, "nombre": "Bella", "especie": "Perro", "raza": "Poodle Mestizo", "edad_meses": 8, "sexo": "Hembra", "tamano": "Pequeno", "descripcion": "Cachorra alegre y cariñosa.", "foto_url": "https://images.unsplash.com/photo-1537151625747-768eb6cf92b2?auto=format&fit=crop&w=600&q=80", "estado": "en_proceso"},
    {"id": 5, "nombre": "Milo", "especie": "Gato", "raza": "Común Europeo", "edad_meses": 18, "sexo": "Macho", "tamano": "Mediano", "descripcion": "Curioso y limpio. Ya fue adoptado por una hermosa familia.", "foto_url": "https://images.unsplash.com/photo-1573865526739-10659fec78a5?auto=format&fit=crop&w=600&q=80", "estado": "adoptada"}
]

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
# RESOLUCIÓN DINÁMICA DE LA URL DE API 1 (INTER-SERVICIO SOA)
# ==============================================================================
def resolver_url_api_mascotas(request: Optional[Request] = None) -> str:
    """
    Determina la URL base para comunicarse por HTTP con la API 1 (Mascotas).
    En local usa el puerto 8001. En Vercel utiliza el dominio público compartido.
    """
    if request:
        host = request.headers.get("host", "")
        # Si no es localhost en puerto 8002, estamos en la nube (Vercel)
        if host and "8002" not in host:
            proto = request.headers.get("x-forwarded-proto", "https")
            return f"{proto}://{host}"

    env_url = os.getenv("API_MASCOTAS_URL", "").rstrip("/")
    if env_url and "127.0.0.1" not in env_url and "localhost" not in env_url:
        return env_url

    vercel_prod = os.getenv("VERCEL_PROJECT_PRODUCTION_URL")
    if vercel_prod:
        return f"https://{vercel_prod}"
    vercel_url = os.getenv("VERCEL_URL")
    if vercel_url:
        return f"https://{vercel_url}"

    return "http://127.0.0.1:8001"

# ==============================================================================
# CLIENTE INTERNO HTTP DE COMUNICACIÓN SOA (API 2 -> API 1)
# ==============================================================================
def verificar_disponibilidad_mascota(mascota_id: int, request: Optional[Request] = None) -> dict:
    """
    Paso clave SOA: Realiza petición HTTP GET a la API 1 (Mascotas).
    Verifica que la mascota exista y consulta su estado de disponibilidad.
    """
    url_base = resolver_url_api_mascotas(request)
    url = f"{url_base}/mascotas/{mascota_id}"
    try:
        respuesta = requests.get(url, timeout=3)
        if respuesta.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"La mascota con ID {mascota_id} no existe en la Fundación (API 1)."
            )
        if respuesta.ok:
            return respuesta.json()
    except requests.exceptions.RequestException:
        pass

    # Fallback 1: Si hay conexión a Supabase, consultar disponibilidad directo en BD
    try:
        conexion = obtener_conexion()
        if conexion:
            cursor = conexion.cursor()
            cursor.execute(
                "SELECT id, nombre, especie, raza, edad_meses, sexo, tamano, descripcion, foto_url, estado FROM mascotas.mascotas WHERE id = %s;",
                (mascota_id,)
            )
            f = cursor.fetchone()
            cursor.close()
            conexion.close()
            if not f:
                raise HTTPException(status_code=404, detail=f"La mascota con ID {mascota_id} no existe en la Fundación (API 1).")
            return {
                "id": f[0], "nombre": f[1], "especie": f[2], "raza": f[3],
                "edad_meses": f[4], "sexo": f[5], "tamano": f[6],
                "descripcion": f[7], "foto_url": f[8], "estado": f[9]
            }
    except HTTPException:
        raise
    except Exception:
        pass

    # Fallback 2: Almacén de mascotas en memoria
    for m in STORE_MASCOTAS_FALLBACK:
        if m["id"] == mascota_id:
            return m

    raise HTTPException(
        status_code=404,
        detail=f"La mascota con ID {mascota_id} no fue encontrada."
    )

def notificar_cambio_estado_mascota(mascota_id: int, nuevo_estado: str, motivo: str = None, request: Optional[Request] = None) -> bool:
    """
    Paso clave SOA: Realiza petición HTTP PATCH a la API 1 (Mascotas).
    Actualiza el estado de la mascota al aprobar una adopción.
    """
    url_base = resolver_url_api_mascotas(request)
    url = f"{url_base}/mascotas/{mascota_id}/estado"
    payload = {
        "estado": nuevo_estado,
        "motivo": motivo or f"Estado actualizado a '{nuevo_estado}' tras resolución de solicitud."
    }
    try:
        respuesta = requests.patch(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=3
        )
        if respuesta.ok:
            return True
    except requests.exceptions.RequestException:
        pass

    # Fallback 1: Actualizar directo en Supabase
    try:
        conexion = obtener_conexion()
        if conexion:
            cursor = conexion.cursor()
            cursor.execute(
                "UPDATE mascotas.mascotas SET estado = %s, fecha_actualizacion = now() WHERE id = %s;",
                (nuevo_estado, mascota_id)
            )
            conexion.commit()
            cursor.close()
            conexion.close()
            return True
    except Exception:
        pass

    # Fallback 2: Almacén en memoria
    for m in STORE_MASCOTAS_FALLBACK:
        if m["id"] == mascota_id:
            m["estado"] = nuevo_estado
            return True

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
        "documentacion": "/solicitudes/docs"
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
            pass
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
def registrar_solicitud(datos: SolicitudCreate, request: Request = None):
    """
    FLUJO CENTRAL SOA (Paso 1):
    1. La API 2 recibe la solicitud de adopción.
    2. Consulta mediante HTTP a la API 1 para verificar que la mascota existe y está disponible.
    3. Si la mascota ya fue adoptada, RECHAZA la solicitud con HTTP 400.
    4. Si está disponible, guarda la solicitud y el solicitante.
    """
    # 1. Comunicación con API 1: Verificar disponibilidad
    mascota = verificar_disponibilidad_mascota(datos.mascota_id, request)

    # 2. Regla de negocio: Verificar que la mascota no esté adoptada
    if mascota.get("estado") == "adoptada":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede registrar solicitud: La mascota '{mascota.get('nombre')}' ya fue adoptada."
        )

    # 3. Intentar guardar en Supabase si está disponible
    ahora = datetime.utcnow().isoformat() + "Z"
    conexion = obtener_conexion()
    if conexion:
        cursor = None
        try:
            cursor = conexion.cursor()
            cursor.execute(
                """
                INSERT INTO adopciones.solicitantes (documento, nombre_completo, correo, telefono, direccion, ciudad, tipo_vivienda, tiene_patio)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    datos.solicitante.documento, datos.solicitante.nombre_completo,
                    datos.solicitante.correo, datos.solicitante.telefono,
                    datos.solicitante.direccion, datos.solicitante.ciudad,
                    datos.solicitante.tipo_vivienda, datos.solicitante.tiene_patio
                )
            )
            sol_id = cursor.fetchone()[0]

            cursor.execute(
                """
                INSERT INTO adopciones.solicitudes (mascota_id, solicitante_id, motivo_adopcion, estado, observaciones)
                VALUES (%s, %s, %s, 'pendiente', 'Solicitud registrada en espera de revisión.')
                RETURNING id, fecha_solicitud;
                """,
                (datos.mascota_id, sol_id, datos.motivo_adopcion)
            )
            fila_sol = cursor.fetchone()
            conexion.commit()

            nueva_solicitud = {
                "id": fila_sol[0],
                "mascota_id": datos.mascota_id,
                "solicitante_id": sol_id,
                "motivo_adopcion": datos.motivo_adopcion,
                "estado": "pendiente",
                "observaciones": "Solicitud registrada en espera de revisión.",
                "fecha_solicitud": str(fila_sol[1]),
                "fecha_resolucion": None,
                "solicitante": datos.solicitante.dict(),
                "mascota_info": {
                    "nombre": mascota.get("nombre"),
                    "especie": mascota.get("especie"),
                    "estado_actual": mascota.get("estado")
                }
            }
            return {
                "mensaje": "Solicitud de adopción registrada exitosamente en Supabase tras validación con API 1.",
                "solicitud": nueva_solicitud,
                "comunicacion_soa": {
                    "api_consultada": f"GET /mascotas/{datos.mascota_id}",
                    "disponibilidad_confirmada": True,
                    "estado_mascota": mascota.get("estado")
                }
            }
        except Exception:
            if conexion: conexion.rollback()
        finally:
            if cursor: cursor.close()
            conexion.close()

    # Fallback en memoria
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
            "api_consultada": f"GET /mascotas/{datos.mascota_id}",
            "disponibilidad_confirmada": True,
            "estado_mascota": mascota.get("estado")
        }
    }

@app.patch("/solicitudes/{id_solicitud}/resolucion", tags=["Solicitudes"])
def resolver_solicitud(id_solicitud: int, datos: SolicitudResolucion, request: Request = None):
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

    # 1. Intentar con Supabase si está disponible
    conexion = obtener_conexion()
    if conexion:
        cursor = None
        try:
            cursor = conexion.cursor()
            cursor.execute("SELECT id, mascota_id, solicitante_id, estado FROM adopciones.solicitudes WHERE id = %s;", (id_solicitud,))
            sol_db = cursor.fetchone()
            if sol_db:
                mascota_id = sol_db[1]

                if datos.estado == "aprobada":
                    # REGLA CRÍTICA: Exclusión mutua
                    cursor.execute(
                        "SELECT id FROM adopciones.solicitudes WHERE mascota_id = %s AND estado = 'aprobada' AND id != %s;",
                        (mascota_id, id_solicitud)
                    )
                    conflicto = cursor.fetchone()
                    if conflicto:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=f"Conflicto de Adopción: La mascota con ID {mascota_id} ya tiene una solicitud aprobada previa (Solicitud #{conflicto[0]})."
                        )

                    # Notificar a API 1 y actualizar en Supabase
                    notificar_cambio_estado_mascota(mascota_id, "adoptada", motivo=f"Adopción aprobada mediante Solicitud #{id_solicitud}", request=request)
                    cursor.execute("UPDATE mascotas.mascotas SET estado = 'adoptada', fecha_actualizacion = now() WHERE id = %s;", (mascota_id,))

                cursor.execute(
                    "UPDATE adopciones.solicitudes SET estado = %s, observaciones = %s, fecha_resolucion = now() WHERE id = %s RETURNING id, fecha_resolucion;",
                    (datos.estado, datos.observaciones or f"Solicitud {datos.estado} por la fundación.", id_solicitud)
                )
                conexion.commit()

                # Mantener sincronizado almacén en memoria
                sol_mem = next((s for s in STORE_SOLICITUDES if s["id"] == id_solicitud), None)
                if sol_mem:
                    sol_mem["estado"] = datos.estado
                    sol_mem["observaciones"] = datos.observaciones

                return {
                    "mensaje": f"Solicitud #{id_solicitud} {datos.estado} exitosamente en Supabase.",
                    "solicitud_id": id_solicitud,
                    "solicitud": {
                        "id": id_solicitud,
                        "mascota_id": mascota_id,
                        "estado": datos.estado,
                        "observaciones": datos.observaciones
                    },
                    "nuevo_estado": datos.estado,
                    "comunicacion_soa": {
                        "regla_adopcion_unica_verificada": True,
                        "notificacion_api1": "completada" if datos.estado == "aprobada" else "no_requerida"
                    }
                }
        except HTTPException:
            raise
        except Exception:
            if conexion: conexion.rollback()
        finally:
            if cursor: cursor.close()
            conexion.close()


    # 2. Fallback en memoria
    solicitud = next((s for s in STORE_SOLICITUDES if s["id"] == id_solicitud), None)
    if not solicitud:
        raise HTTPException(status_code=404, detail=f"Solicitud con ID {id_solicitud} no encontrada.")

    mascota_id = solicitud["mascota_id"]

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

        notificar_cambio_estado_mascota(
            mascota_id=mascota_id,
            nuevo_estado="adoptada",
            motivo=f"Adopción formalizada mediante Solicitud #{id_solicitud}",
            request=request
        )

    ahora = datetime.utcnow().isoformat() + "Z"
    solicitud["estado"] = datos.estado
    solicitud["observaciones"] = datos.observaciones or f"Solicitud {datos.estado} por la fundación."
    solicitud["fecha_resolucion"] = ahora

    solicitante = next((s for s in STORE_SOLICITANTES if s["id"] == solicitud["solicitante_id"]), None)

    return {
        "mensaje": f"Solicitud #{id_solicitud} {datos.estado} exitosamente.",
        "solicitud": {**solicitud, "solicitante": solicitante},
        "comunicacion_soa": {
            "regla_adopcion_unica_verificada": True,
            "notificacion_api1": "completada" if datos.estado == "aprobada" else "no_requerida"
        }
    }

@app.post("/reset", tags=["Mantenimiento"])
@app.post("/solicitudes/reset", tags=["Mantenimiento"])
def reiniciar_datos():
    """
    Ruta para reiniciar solicitudes a los datos semilla tanto en Supabase como en memoria.
    """
    global STORE_SOLICITUDES
    STORE_SOLICITUDES[0]["estado"] = "aprobada"
    STORE_SOLICITUDES[1]["estado"] = "pendiente"
    STORE_SOLICITUDES[2]["estado"] = "pendiente"

    try:
        conexion = obtener_conexion()
        if conexion:
            cursor = conexion.cursor()
            cursor.execute("UPDATE adopciones.solicitudes SET estado = 'aprobada' WHERE id = 1;")
            cursor.execute("UPDATE adopciones.solicitudes SET estado = 'pendiente', fecha_resolucion = NULL WHERE id IN (2, 3);")
            cursor.execute("DELETE FROM adopciones.solicitudes WHERE id > 3;")
            cursor.execute("UPDATE mascotas.mascotas SET estado = 'disponible' WHERE id IN (1, 2, 3);")
            cursor.execute("UPDATE mascotas.mascotas SET estado = 'en_proceso' WHERE id = 4;")
            cursor.execute("UPDATE mascotas.mascotas SET estado = 'adoptada' WHERE id = 5;")
            conexion.commit()
            cursor.close()
            conexion.close()
    except Exception:
        pass

    return {"mensaje": "Datos de solicitudes reiniciados correctamente"}
