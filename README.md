# 🐶 Huellas de Esperanza · Plataforma Web de Adopción Responsable
### Segundo Examen de Arquitectura Orientada a Servicios (SOA) · UFPS

Plataforma modular construida bajo los principios de la **Arquitectura Orientada a Servicios (SOA)**. Desacopla la gestión del catálogo de animales y su disponibilidad de la administración y resolución de solicitudes de adopción responsable.

---

## 🏛️ Estructura del Proyecto

```text
segundo parcial AOS/
├── api-mascotas/            # Microservicio 1: Gestión de Mascotas y Disponibilidad
│   ├── main.py              # Endpoints FastAPI (Puerto 8001) y Swagger UI (/docs)
│   ├── con_db.py            # Módulo de conexión a Supabase con fallback local
│   └── requirements.txt     # Dependencias de API 1
│
├── api-adopciones/          # Microservicio 2: Gestión de Solicitudes y Solicitantes
│   ├── main.py              # Endpoints FastAPI (Puerto 8002) y cliente HTTP inter-servicio
│   ├── con_db.py            # Módulo de conexión a Supabase con fallback local
│   └── requirements.txt     # Dependencias de API 2
│
├── database/                # Scripts SQL de Base de Datos
│   ├── schema.sql           # Esquemas independientes 'mascotas' y 'adopciones' + RLS + Índice único
│   └── seed.sql             # Datos iniciales para pruebas
│
├── web/                     # Frontend Web Responsivo (Capa de Presentación)
│   ├── index.html           # SPA con tabs: Catálogo, Solicitudes y Arquitectura
│   ├── css/estilos.css      # Hoja de estilos moderna y responsiva
│   └── js/app.js            # Lógica cliente para consumir API 1 y API 2
│
├── docs/                    # Documentación formal de entrega
│   ├── Aterrizando_mi_proyecto_SOA_HuellasDeEsperanza.md    # Documento en Markdown
│   └── Aterrizando_mi_proyecto_SOA_HuellasDeEsperanza.docx  # Documento en formato Word
│
├── tests/                   # Suite de Pruebas Automatizadas
│   └── test_inter_service_soa.py # Pruebas pytest de integración y regla de oro
│
├── vercel.json              # Configuración de despliegue en Vercel (@vercel/python y static)
├── .env.example             # Plantilla de variables de entorno
└── README.md                # Guía técnica y manual de ejecución
```

---

## 🚀 Puesta en Marcha Local (Paso a Paso)

### 1. Requisitos Previos
* Python 3.10 o superior (instalado con `py` o `python`).
* Navegador web moderno.

### 2. Instalación de Dependencias
Abre una terminal PowerShell o CMD en la carpeta del proyecto y ejecuta:

```powershell
py -m pip install fastapi uvicorn pydantic requests psycopg2-binary python-dotenv pytest httpx python-docx
```

### 3. Ejecución de los Microservicios

Para probar el flujo completo en tu máquina local, abre **dos terminales independientes**:

#### Terminal 1 — Iniciar API 1 (Mascotas en Puerto 8001):
```powershell
cd "api-mascotas"
py -m uvicorn main:app --port 8001 --reload
```
* Swagger API 1: [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)

#### Terminal 2 — Iniciar API 2 (Adopciones en Puerto 8002):
```powershell
cd "api-adopciones"
py -m uvicorn main:app --port 8002 --reload
```
* Swagger API 2: [http://127.0.0.1:8002/docs](http://127.0.0.1:8002/docs)

### 4. Abrir la Aplicación Web (Frontend)
Simplemente abre el archivo `web/index.html` en tu navegador o sírvelo con cualquier servidor estático (como Live Server de VS Code o `py -m http.server 3000 --directory web`).

---

## 🧪 Ejecución de Pruebas Automatizadas

El proyecto incluye 12 pruebas automatizadas con **pytest** que verifican el correcto funcionamiento de cada endpoint y la regla de oro:

```powershell
py -m pytest tests/ -v
```

Resultado esperado:
```text
tests/test_inter_service_soa.py::test_api1_health_check PASSED
tests/test_inter_service_soa.py::test_api1_listar_mascotas PASSED
tests/test_inter_service_soa.py::test_api1_filtrar_mascotas_por_especie PASSED
tests/test_inter_service_soa.py::test_api1_consultar_detalle_mascota PASSED
tests/test_inter_service_soa.py::test_api1_registrar_nueva_mascota PASSED
tests/test_inter_service_soa.py::test_api1_actualizar_estado_mascota PASSED
tests/test_inter_service_soa.py::test_api2_health_check PASSED
tests/test_inter_service_soa.py::test_api2_listar_solicitudes PASSED
tests/test_inter_service_soa.py::test_api2_registrar_solicitud_mascota_disponible PASSED
tests/test_inter_service_soa.py::test_api2_rechazar_solicitud_si_mascota_ya_adoptada PASSED
tests/test_inter_service_soa.py::test_api2_aprobar_solicitud_y_notificar_cambio PASSED
tests/test_inter_service_soa.py::test_api2_regla_oro_evitar_dos_adopciones_aprobadas_misma_mascota PASSED

======================= 12 passed in 7.5s =======================
```

---

## 🔄 Flujo de Comunicación Inter-Servicio SOA

```text
1. Ciudadano envía solicitud de adopción en la Web.
   │
   ▼
2. API 2 (Adopciones) recibe POST /solicitudes.
   │
   ├─► Realiza GET http://127.0.0.1:8001/mascotas/{id} hacia API 1.
   │   └─ Si estado == 'adoptada', responde HTTP 400 Bad Request.
   │   └─ Si está disponible, guarda la solicitud en estado 'pendiente'.
   │
3. Evaluador hace clic en "Aprobar" en la Web.
   │
   ▼
4. API 2 recibe PATCH /solicitudes/{id}/resolucion con estado='aprobada'.
   │
   ├─► [REGLA CRÍTICA DEL EXAMEN]: Verifica que no exista OTRA solicitud
   │   aprobada para la misma mascota.
   │   └─ Si ya existe otra: responde HTTP 409 Conflict.
   │
   └─► Si es válida: Despacha PATCH http://127.0.0.1:8001/mascotas/{id}/estado
       marcando a la mascota como 'adoptada' en API 1.
```

---

## 🗄️ Base de Datos en Supabase (Opcional)

Si deseas conectar a tu proyecto real en Supabase:
1. Copia el archivo `.env.example` a `.env` y coloca las credenciales de tu base de datos PostgreSQL.
2. Ingresa al **SQL Editor** de tu proyecto Supabase y ejecuta el script `database/schema.sql` seguido de `database/seed.sql`.
3. *Nota:* Si no configuras Supabase, los microservicios activan automáticamente su **almacén determinista en memoria**, permitiendo ejecutar y evaluar el 100% de las funcionalidades sin dependencias externas.
