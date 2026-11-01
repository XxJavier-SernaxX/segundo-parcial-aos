"""
Conjunto de Pruebas Automatizadas de Integración SOA
Plataforma: Fundación Huellas de Esperanza
Objetivo: Validar los endpoints de API 1, API 2 y la regla de oro:
"Evitar que una misma mascota tenga dos adopciones aprobadas" (HTTP 409 Conflict)
"""

import sys
import os
import importlib.util
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent
DIR_API1 = BASE_DIR / "api-mascotas"
DIR_API2 = BASE_DIR / "api-adopciones"

# Asegurar directorios en sys.path para resolución de con_db
if str(DIR_API1) not in sys.path:
    sys.path.insert(0, str(DIR_API1))
if str(DIR_API2) not in sys.path:
    sys.path.insert(0, str(DIR_API2))

# Cargar modulo API 1 con nombre único
spec1 = importlib.util.spec_from_file_location("api_mascotas_module", DIR_API1 / "main.py")
modulo_mascotas = importlib.util.module_from_spec(spec1)
sys.modules["main_mascotas"] = modulo_mascotas
spec1.loader.exec_module(modulo_mascotas)

# Cargar modulo API 2 con nombre único
spec2 = importlib.util.spec_from_file_location("api_adopciones_module", DIR_API2 / "main.py")
modulo_adopciones = importlib.util.module_from_spec(spec2)
sys.modules["main_adopciones"] = modulo_adopciones
spec2.loader.exec_module(modulo_adopciones)

client_mascotas = TestClient(modulo_mascotas.app)
client_adopciones = TestClient(modulo_adopciones.app)


@pytest.fixture(autouse=True)
def reiniciar_datos_prueba():
    """Reinicia el estado en memoria antes de cada test para asegurar determinismo."""
    modulo_mascotas.reiniciar_datos()
    modulo_adopciones.reiniciar_datos()


# ==============================================================================
# PRUEBAS API 1: SERVICIO DE MASCOTAS
# ==============================================================================
def test_api1_health_check():
    """Verifica el estado de salud de la API 1."""
    response = client_mascotas.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["servicio"] == "API 1 · Mascotas"
    assert data["estado"] == "online"


def test_api1_listar_mascotas():
    """Verifica que se liste el catálogo de mascotas."""
    response = client_mascotas.get("/mascotas")
    assert response.status_code == 200
    mascotas = response.json()
    assert isinstance(mascotas, list)
    assert len(mascotas) >= 5
    nombres = [m["nombre"] for m in mascotas]
    assert "Max" in nombres
    assert "Luna" in nombres


def test_api1_filtrar_mascotas_por_especie():
    """Verifica el filtrado por especie en API 1."""
    response = client_mascotas.get("/mascotas?especie=Gato")
    assert response.status_code == 200
    gatos = response.json()
    for g in gatos:
        assert g["especie"] == "Gato"


def test_api1_consultar_detalle_mascota():
    """Verifica la consulta individual por ID."""
    response = client_mascotas.get("/mascotas/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["nombre"] == "Max"
    assert data["estado"] == "disponible"


def test_api1_registrar_nueva_mascota():
    """Verifica el registro de un nuevo animal en el sistema."""
    nueva = {
        "nombre": "Firulais",
        "especie": "Perro",
        "raza": "Beagle",
        "edad_meses": 18,
        "sexo": "Macho",
        "tamano": "Mediano",
        "descripcion": "Muy activo y juguetón",
        "foto_url": "https://images.unsplash.com/photo-example"
    }
    response = client_mascotas.post("/mascotas", json=nueva)
    assert response.status_code == 201
    data = response.json()
    assert data["nombre"] == "Firulais"
    assert data["estado"] == "disponible"
    assert "id" in data


def test_api1_actualizar_estado_mascota():
    """Verifica el endpoint PATCH que será invocado por API 2 al aprobar adopción."""
    payload = {
        "estado": "en_proceso",
        "motivo": "Evaluación domiciliaria en curso"
    }
    response = client_mascotas.patch("/mascotas/1/estado", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["estado"] == "en_proceso"

    # Verificar que el estado cambió al consultar
    resp_detalle = client_mascotas.get("/mascotas/1")
    assert resp_detalle.json()["estado"] == "en_proceso"


# ==============================================================================
# PRUEBAS API 2: SERVICIO DE ADOPCIONES
# ==============================================================================
def test_api2_health_check():
    """Verifica el estado de salud de la API 2."""
    response = client_adopciones.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["servicio"] == "API 2 · Adopciones"
    assert data["estado"] == "online"


def test_api2_listar_solicitudes():
    """Verifica la consulta de solicitudes de adopción."""
    response = client_adopciones.get("/solicitudes")
    assert response.status_code == 200
    solicitudes = response.json()
    assert isinstance(solicitudes, list)
    assert len(solicitudes) >= 3


def test_api2_registrar_solicitud_mascota_disponible():
    """Verifica el registro exitoso de una solicitud para una mascota disponible."""
    payload = {
        "mascota_id": 2, # Luna está disponible
        "solicitante": {
            "documento": "1090777888",
            "nombre_completo": "Ana Patricia Mendoza",
            "correo": "ana.mendoza@gmail.com",
            "telefono": "3154445566",
            "direccion": "Calle 15 # 4-30",
            "ciudad": "Cúcuta",
            "tipo_vivienda": "Apartamento",
            "tiene_patio": False
        },
        "motivo_adopcion": "Quiero darle mucho amor a Luna en mi hogar."
    }
    response = client_adopciones.post("/solicitudes", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "solicitud" in data
    assert data["solicitud"]["estado"] == "pendiente"
    assert data["solicitud"]["mascota_id"] == 2


def test_api2_rechazar_solicitud_si_mascota_ya_adoptada():
    """
    Verifica que la API 2 rechace con 400 Bad Request registrar una solicitud
    si la mascota ya fue adoptada (Mascota #5 Milo ya está adoptada).
    """
    payload = {
        "mascota_id": 5, # Milo está adoptada
        "solicitante": {
            "documento": "1090123456",
            "nombre_completo": "Pedro Pérez",
            "correo": "pedro@test.com",
            "telefono": "3111112233",
            "direccion": "Av 0",
            "ciudad": "Cúcuta",
            "tipo_vivienda": "Casa",
            "tiene_patio": True
        },
        "motivo_adopcion": "Deseo adoptar a Milo"
    }
    response = client_adopciones.post("/solicitudes", json=payload)
    assert response.status_code == 400
    assert "ya fue adoptada" in response.json()["detail"].lower()


# ==============================================================================
# PRUEBAS REGLA DE ORO DEL EXAMEN (CONCURRENCIA / EXCLUSIÓN MUTUA SOA)
# ==============================================================================
def test_api2_aprobar_solicitud_y_notificar_cambio():
    """
    Verifica el flujo exitoso de aprobación:
    1. Se aprueba la solicitud #3 para la Mascota #1 (Max).
    2. API 2 actualiza la solicitud a 'aprobada'.
    3. API 2 notifica a API 1 para marcar la Mascota como 'adoptada'.
    """
    payload_resolucion = {
        "estado": "aprobada",
        "observaciones": "Aprobado tras entrevista satisfactoria."
    }
    response = client_adopciones.patch("/solicitudes/3/resolucion", json=payload_resolucion)
    assert response.status_code == 200
    data = response.json()
    assert data["solicitud"]["estado"] == "aprobada"
    assert data["comunicacion_soa"]["regla_adopcion_unica_verificada"] is True

    # Verificar que en API 1 la mascota #1 quedó como 'adoptada'
    resp_m1 = client_mascotas.get("/mascotas/1")
    assert resp_m1.json()["estado"] == "adoptada"


def test_api2_regla_oro_evitar_dos_adopciones_aprobadas_misma_mascota():
    """
    CRÍTICO PARA EL EXAMEN:
    'Evitar que una misma mascota tenga dos adopciones aprobadas'
    1. La mascota #5 (Milo) ya tiene la solicitud #1 en estado 'aprobada'.
    2. Creamos una segunda solicitud ficticia para la mascota #5 y tratamos de aprobarla.
    3. API 2 DEBE responder con HTTP 409 Conflict rechazando la operación.
    """
    nueva_sol_id = 999
    modulo_adopciones.STORE_SOLICITUDES.append({
        "id": nueva_sol_id,
        "mascota_id": 5, # Misma mascota que la solicitud #1 (Milo)
        "solicitante_id": 2,
        "motivo_adopcion": "Intento de segunda adopción indebida",
        "estado": "pendiente",
        "observaciones": None,
        "fecha_solicitud": "2026-11-01T12:00:00Z",
        "fecha_resolucion": None
    })

    # Intentar aprobar esta segunda solicitud para la mascota #5
    payload = {
        "estado": "aprobada",
        "observaciones": "Intento ilegal de aprobar dos veces la misma mascota"
    }
    response = client_adopciones.patch(f"/solicitudes/{nueva_sol_id}/resolucion", json=payload)

    # Debe retornar HTTP 409 Conflicto
    assert response.status_code == 409
    data = response.json()
    assert "ya tiene una solicitud aprobada previa" in data["detail"]
