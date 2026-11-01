-- ==============================================================================
-- PROYECTO: Huellas de Esperanza - Plataforma de Adopción Responsable de Mascotas
-- EXAMEN 2: ARQUITECTURA ORIENTADA A SERVICIOS (SOA)
-- Base de Datos: PostgreSQL mediante Supabase
-- Separación de Esquemas: mascotas (API 1) y adopciones (API 2)
-- ==============================================================================

-- Habilitar extensión para generación de identificadores UUID si se requiere
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==============================================================================
-- 1. ESQUEMA: mascotas (Propiedad exclusiva de API 1 - Servicio de Mascotas)
-- ==============================================================================
CREATE SCHEMA IF NOT EXISTS mascotas;

-- Tabla: mascotas.mascotas
-- Estados permitidos:
--   - 'disponible': Lista para recibir solicitudes de adopción.
--   - 'en_proceso': Tiene solicitudes en evaluación o una solicitud aprobada pendiente de entrega.
--   - 'adoptada': Adopción completada con éxito. No admite nuevas solicitudes.
CREATE TABLE IF NOT EXISTS mascotas.mascotas (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    especie VARCHAR(50) NOT NULL CHECK (especie IN ('Perro', 'Gato', 'Otro')),
    raza VARCHAR(100) NOT NULL DEFAULT 'Mestizo',
    edad_meses INTEGER NOT NULL CHECK (edad_meses >= 0),
    sexo VARCHAR(20) NOT NULL CHECK (sexo IN ('Macho', 'Hembra')),
    tamano VARCHAR(20) NOT NULL CHECK (tamano IN ('Pequeno', 'Mediano', 'Grande')),
    descripcion TEXT,
    foto_url TEXT,
    estado VARCHAR(30) NOT NULL DEFAULT 'disponible' CHECK (estado IN ('disponible', 'en_proceso', 'adoptada')),
    fecha_ingreso TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    fecha_actualizacion TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Índices de consulta rápida en esquema mascotas
CREATE INDEX IF NOT EXISTS idx_mascotas_estado ON mascotas.mascotas(estado);
CREATE INDEX IF NOT EXISTS idx_mascotas_especie ON mascotas.mascotas(especie);

-- ==============================================================================
-- 2. ESQUEMA: adopciones (Propiedad exclusiva de API 2 - Servicio de Adopciones)
-- ==============================================================================
CREATE SCHEMA IF NOT EXISTS adopciones;

-- Tabla: adopciones.solicitantes
CREATE TABLE IF NOT EXISTS adopciones.solicitantes (
    id SERIAL PRIMARY KEY,
    documento VARCHAR(30) UNIQUE NOT NULL,
    nombre_completo VARCHAR(150) NOT NULL,
    correo VARCHAR(150) NOT NULL,
    telefono VARCHAR(30) NOT NULL,
    direccion VARCHAR(200) NOT NULL,
    ciudad VARCHAR(100) NOT NULL DEFAULT 'Cúcuta',
    tipo_vivienda VARCHAR(50) NOT NULL DEFAULT 'Casa' CHECK (tipo_vivienda IN ('Casa', 'Apartamento', 'Finca')),
    tiene_patio BOOLEAN DEFAULT true NOT NULL,
    fecha_registro TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Tabla: adopciones.solicitudes
-- Estados permitidos:
--   - 'pendiente': Solicitud registrada, en espera de revisión.
--   - 'aprobada': Solicitud aceptada por la fundación (la mascota pasa a 'adoptada' o 'en_proceso').
--   - 'rechazada': Solicitud denegada.
CREATE TABLE IF NOT EXISTS adopciones.solicitudes (
    id SERIAL PRIMARY KEY,
    mascota_id INTEGER NOT NULL, -- Referencia lógica hacia API 1 (Sin JOIN físico entre esquemas)
    solicitante_id INTEGER NOT NULL REFERENCES adopciones.solicitantes(id) ON DELETE CASCADE,
    motivo_adopcion TEXT NOT NULL,
    estado VARCHAR(30) NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'aprobada', 'rechazada')),
    observaciones TEXT,
    fecha_solicitud TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    fecha_resolucion TIMESTAMP WITH TIME ZONE
);

-- Índice único parcial crucial:
-- Regla de negocio del examen: "Evitar que una misma mascota tenga dos adopciones aprobadas"
CREATE UNIQUE INDEX IF NOT EXISTS idx_adopcion_unica_aprobada 
ON adopciones.solicitudes(mascota_id) 
WHERE estado = 'aprobada';

CREATE INDEX IF NOT EXISTS idx_solicitudes_mascota ON adopciones.solicitudes(mascota_id);
CREATE INDEX IF NOT EXISTS idx_solicitudes_estado ON adopciones.solicitudes(estado);

-- ==============================================================================
-- 3. POLÍTICAS ROW LEVEL SECURITY (RLS) EN SUPABASE
-- ==============================================================================
ALTER TABLE mascotas.mascotas ENABLE ROW LEVEL SECURITY;
ALTER TABLE adopciones.solicitantes ENABLE ROW LEVEL SECURITY;
ALTER TABLE adopciones.solicitudes ENABLE ROW LEVEL SECURITY;

-- Políticas de lectura pública
CREATE POLICY "Lectura pública mascotas" ON mascotas.mascotas FOR SELECT USING (true);
CREATE POLICY "Lectura pública solicitantes" ON adopciones.solicitantes FOR SELECT USING (true);
CREATE POLICY "Lectura pública solicitudes" ON adopciones.solicitudes FOR SELECT USING (true);

-- Políticas de inserción y actualización
CREATE POLICY "Inserción pública mascotas" ON mascotas.mascotas FOR INSERT WITH CHECK (true);
CREATE POLICY "Actualización pública mascotas" ON mascotas.mascotas FOR UPDATE USING (true);
CREATE POLICY "Inserción pública solicitantes" ON adopciones.solicitantes FOR INSERT WITH CHECK (true);
CREATE POLICY "Inserción pública solicitudes" ON adopciones.solicitudes FOR INSERT WITH CHECK (true);
CREATE POLICY "Actualización pública solicitudes" ON adopciones.solicitudes FOR UPDATE USING (true);
