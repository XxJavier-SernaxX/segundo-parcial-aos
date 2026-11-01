# Huellas de Esperanza · Aterrizando mi proyecto SOA
**Arquitectura Orientada a Servicios · UFPS**  
**Integrantes:** [Nombres y Apellidos de los Integrantes del Equipo]  

---

## 1. Nombre, problema y solución

* **Nombre del proyecto:** **Huellas de Esperanza**, plataforma web para la gestión integral y adopción responsable de mascotas rescatadas.
* **Problema:** En Cúcuta y Norte de Santander, los refugios y fundaciones de protección animal operan sus procesos de rescate y adopción de manera informal y descentralizada (publicaciones aisladas en redes sociales, conversaciones por WhatsApp y planillas manuales de cálculo). Esta falta de estandarización ocasiona pérdida de trazabilidad en los antecedentes de los solicitantes, retrasos en la respuesta, y situaciones críticas como la **duplicidad de adopciones** (dos familias aprobadas simultáneamente para el mismo animal) o la permanencia de animales ya adoptados como supuestamente disponibles en los catálogos públicos.
* **Solución:** Una plataforma web fundamentada en una **Arquitectura Orientada a Servicios (SOA)** que separa de manera estricta y modular la gestión del catálogo de animales y su disponibilidad del ciclo de evaluación y resolución de solicitudes de adopción. Permite a la comunidad explorar animales disponibles, postularse con información verificable de su vivienda y tenencia responsable, y a los coordinadores evaluar y resolver solicitudes de forma coordinada, garantizando mediante reglas de negocio inter-servicio que **una misma mascota jamás pueda tener dos adopciones aprobadas**.

---

## 2. Los dos servicios independientes

Siguiendo el principio de autonomía de servicios de SOA, cada microservicio es propietario exclusivo de su dominio funcional y de sus datos:
* **API 1 (Mascotas):** Conoce el inventario de animales, sus características biológicas, vacunas y su estado de disponibilidad (`disponible`, `en_proceso`, `adoptada`).
* **API 2 (Adopciones):** Conoce la identidad de los solicitantes, sus condiciones de vivienda y el ciclo de vida de los trámites de adopción (`pendiente`, `aprobada`, `rechazada`).

Ninguno de los dos servicios puede cumplir el ciclo de adopción sin interactuar con el otro a través de su interfaz de servicios (contrato REST).

### API 1 — Servicio de Mascotas (Principal · Puerto 8001)
Desarrollada con **FastAPI**. Es la única entidad con autoridad para registrar animales y alterar su disponibilidad.
* `GET /health` → Comprobación de salud y estado operativo del servicio.
* `GET /mascotas` → Catálogo de animales rescatados (filtros por `estado` y `especie`).
* `GET /mascotas/{id}` → Consulta detallada de una mascota (utilizado por API 2 para verificar disponibilidad).
* `POST /mascotas` → Registro de un nuevo animal rescatado.
* `PATCH /mascotas/{id}/estado` → Actualización de disponibilidad (`disponible`, `en_proceso`, `adoptada`). Endpoint invocado por API 2 al aprobar adopciones.
* `GET /docs` → Documentación Swagger UI / OpenAPI interactiva.

### API 2 — Servicio de Adopciones (Complementario · Puerto 8002)
Desarrollada con **FastAPI**. Administra los expedientes de solicitantes y la resolución de las solicitudes.
* `GET /health` → Comprobación de salud y estado de conexión con API 1.
* `GET /solicitudes` → Listado de solicitudes con datos consolidados del solicitante.
* `GET /solicitudes/{id}` → Detalle y trazabilidad de una solicitud específica.
* `POST /solicitudes` → Registro de solicitud de adopción con validación previa de disponibilidad hacia API 1.
* `PATCH /solicitudes/{id}/resolucion` → Aprobación o rechazo de solicitud con aplicación de la regla de oro y notificación HTTP hacia API 1.
* `GET /docs` → Documentación Swagger UI / OpenAPI interactiva.

---

## 3. Comunicación inter-servicio (REST sobre HTTP + JSON)

La comunicación entre servicios se realiza de forma sincrónica mediante peticiones HTTP/REST con cuerpos en formato JSON. La API 2 conoce la ubicación de la API 1 a través de la variable de entorno `API_MASCOTAS_URL`:

1. **Validación al registrar solicitud (`POST /solicitudes`):**  
   Antes de radicar la solicitud, la API 2 realiza una petición `GET http://127.0.0.1:8001/mascotas/{id}`.  
   * Si la mascota no existe en API 1, responde `404 Not Found`.
   * Si la mascota ya tiene estado `adoptada`, responde `400 Bad Request` indicando que la mascota ya cuenta con un hogar definitivo.
   * Si está disponible, almacena los datos del solicitante y la solicitud en estado `pendiente`.

2. **Resolución y verificación de exclusión mutua (`PATCH /solicitudes/{id}/resolucion`):**  
   Cuando un evaluador procede a **Aprobar** una solicitud:
   * **Regla crítica del examen:** La API 2 verifica si ya existe otra solicitud en estado `aprobada` para esa misma mascota. Si existe, la operación es abortada de inmediato respondiendo **`HTTP 409 Conflict`** con el mensaje explicativo: *"Conflicto de Adopción: La mascota con ID X ya tiene una solicitud aprobada previa"*.
   * **Notificación de estado:** Si no hay conflicto, la API 2 despacha una petición `PATCH http://127.0.0.1:8001/mascotas/{id}/estado` con `{ "estado": "adoptada", "motivo": "Adopción formalizada" }`.
   * La API 1 actualiza su registro a `adoptada`. De esta manera, el animal deja de estar disponible en el catálogo general.

3. **Rechazo de solicitud:**  
   Si la solicitud es rechazada, la API 2 registra las causales y observaciones sin alterar el estado del animal en la API 1, permitiendo que otros postulantes sigan en evaluación.

---

## 4. Base de datos e interfaz web

### Base de datos (PostgreSQL en Supabase)
La persistencia está dividida en dos esquemas independientes que garantizan el principio de desacoplamiento de datos en SOA:
* **Esquema `mascotas`:**
  * Tabla `mascotas.mascotas` (`id`, `nombre`, `especie`, `raza`, `edad_meses`, `sexo`, `tamano`, `descripcion`, `foto_url`, `estado`, `fecha_ingreso`, `fecha_actualizacion`).
* **Esquema `adopciones`:**
  * Tabla `adopciones.solicitantes` (`id`, `documento`, `nombre_completo`, `correo`, `telefono`, `direccion`, `ciudad`, `tipo_vivienda`, `tiene_patio`).
  * Tabla `adopciones.solicitudes` (`id`, `mascota_id`, `solicitante_id`, `motivo_adopcion`, `estado`, `observaciones`, `fecha_solicitud`, `fecha_resolucion`).

> **Garantía en Base de Datos:** Para reforzar la regla de oro a nivel de persistencia relacional, se diseñó un índice parcial único:  
> `CREATE UNIQUE INDEX idx_adopcion_unica_aprobada ON adopciones.solicitudes (mascota_id) WHERE (estado = 'aprobada');`  
> Esto garantiza que ni por API ni por concurrencia en base de datos una mascota pueda tener dos adopciones aprobadas.

### Interfaz Web (SPA Responsiva en HTML5, CSS3 y Vanilla JavaScript)
* **Catálogo de Mascotas:** Tarjetas interactivas con fotografías, detalles de edad, tamaño, raza y badges de disponibilidad (`Disponible`, `En Proceso`, `Ya Adoptado`).
* **Formulario de Postulación (Modal):** Permite ingresar documento, contacto, tipo de vivienda, disponibilidad de patio y motivos de adopción.
* **Módulo de Gestión de Solicitudes:** Tabla administrativa para revisar cada postulante, con botones directos para **Aprobar** o **Rechazar**. Muestra alertas visuales dinámicas ante cualquier conflicto de concurrencia.
* **Panel de Arquitectura SOA & Swagger:** Acceso directo a los Swagger `/docs` de ambas APIs y una consola interactiva integrada para ejecutar peticiones JSON en vivo.

---

## 5. Esquema de arquitectura

```text
+-----------------------------------------------------------------------------------------+
|                                    CAPA DE CLIENTE                                      |
|                                                                                         |
|                    Frontend Web Responsivo (HTML5 / CSS3 / Vanilla JS)                  |
|                    - Catálogo de Mascotas   - Formulario de Adopción                    |
|                    - Panel de Solicitudes   - Consola Swagger Interactiva               |
+------------------------------------+------------------------------------+---------------+
                                     |                                    |
                    Peticiones HTTP  |                   Peticiones HTTP  |
                    (REST / JSON)    |                   (REST / JSON)    |
                                     v                                    v
+----------------------------------------+       COMUNICACIÓN     +----------------------------------------+
|                 API 1                  |        ENTRE APIS      |                 API 2                  |
|          SERVICIO DE MASCOTAS          |<-----------------------|         SERVICIO DE ADOPCIONES         |
|         FastAPI (Puerto 8001)          |   1. GET /mascotas/{id}|         FastAPI (Puerto 8002)          |
|                                        |      (Verifica estado) |                                        |
|  Endpoints:                            |   2. PATCH /estado     |  Endpoints:                            |
|  - GET   /mascotas                     |      (Marca 'adoptada')|  - GET   /solicitudes                  |
|  - GET   /mascotas/{id}                |----------------------->|  - POST  /solicitudes                  |
|  - POST  /mascotas                     |   Regla de Oro:        |  - PATCH /solicitudes/{id}/resolucion  |
|  - PATCH /mascotas/{id}/estado         |   Exclusión Mutua      |    * HTTP 409 Conflict si duplica      |
|  - GET   /docs (Swagger UI)            |   (1 adopción/mascota) |  - GET   /docs (Swagger UI)            |
+-------------------+--------------------+                        +-------------------+--------------------+
                    |                                                                 |
                    | SQL                                                             | SQL
                    | (Solo esquema mascotas)                                         | (Solo esquema adopciones)
                    v                                                                 v
+----------------------------------------------------------------------------------------------------------+
|                                      PERSISTENCIA CLOUD (SUPABASE)                                       |
|                                                                                                          |
|          Esquema: mascotas                                          Esquema: adopciones                  |
|          - Tabla mascotas.mascotas                                  - Tabla adopciones.solicitantes      |
|                                                                     - Tabla adopciones.solicitudes       |
|                                                                     - UNIQUE INDEX (mascota_id)          |
|                                                                       WHERE estado = 'aprobada'          |
+----------------------------------------------------------------------------------------------------------+
```

---

## 6. Resultado esperado y ciclo demostrable

Se demostrará en la nube (Vercel + Supabase) y en entorno local el ciclo completo de adopción responsable:
1. **Consulta inicial:** El usuario ingresa a la plataforma y observa a *Max* (Perro) y *Luna* (Gato) en estado `Disponible`.
2. **Envío de solicitud:** El usuario postula su adopción para *Max*. La **API 2** consulta a la **API 1** (`GET /mascotas/1`), corrobora que está disponible y radica la solicitud #3 en estado `pendiente`.
3. **Aprobación coordinada:** El coordinador evalúa el expediente y aprueba la solicitud. La **API 2** verifica que *Max* no tenga ninguna otra adopción aprobada y emite un `PATCH /mascotas/1/estado` a la **API 1** estableciendo el estado en `adoptada`.
4. **Actualización visual:** En la interfaz web, *Max* pasa inmediatamente a badge azul `¡Adoptado!` y su botón de adopción se deshabilita automáticamente.
5. **Comprobación de la regla de oro del examen:** Si otro usuario intentase enviar o aprobar una segunda solicitud de adopción para *Max*, la **API 2** rechaza la operación retornando **`HTTP 409 Conflict`**, demostrando la integridad del flujo distribuido y la satisfacción del 100% de los lineamientos del examen.
