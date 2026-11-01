-- ==============================================================================
-- PROYECTO: Huellas de Esperanza - Datos Semilla Oficiales
-- ==============================================================================

-- 1. Mascotas iniciales (Fundación Huellas de Esperanza)
INSERT INTO mascotas.mascotas (id, nombre, especie, raza, edad_meses, sexo, tamano, descripcion, foto_url, estado) VALUES
(1, 'Max', 'Perro', 'Golden Retriever Mestizo', 24, 'Macho', 'Grande', 
 'Juguetón, sociable con niños y otros perros. Vacunado y esterilizado.', 
 'https://images.unsplash.com/photo-1552053831-71594a27632d?auto=format&fit=crop&w=600&q=80', 'disponible'),

(2, 'Luna', 'Gato', 'Siamés Mestizo', 12, 'Hembra', 'Pequeno', 
 'Tranquila, cariñosa y ronroneadora. Ideal para apartamento.', 
 'https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?auto=format&fit=crop&w=600&q=80', 'disponible'),

(3, 'Rocky', 'Perro', 'Criollo / Labrador', 36, 'Macho', 'Mediano', 
 'Excelente compañero de caminatas, muy obediente y leal.', 
 'https://images.unsplash.com/photo-1543466835-00a7907e9de1?auto=format&fit=crop&w=600&q=80', 'disponible'),

(4, 'Bella', 'Perro', 'Poodle Mestizo', 8, 'Hembra', 'Pequeno', 
 'Cachorrita activa y dulce, rescatada de la zona céntrica.', 
 'https://images.unsplash.com/photo-1583511655857-d19b40a7a54e?auto=format&fit=crop&w=600&q=80', 'en_proceso'),

(5, 'Milo', 'Gato', 'Común Europeo', 18, 'Macho', 'Mediano', 
 'Curioso, limpio y muy juguetón. Ya fue adoptado por una hermosa familia.', 
 'https://images.unsplash.com/photo-1573865526739-10659fec78a5?auto=format&fit=crop&w=600&q=80', 'adoptada')
ON CONFLICT (id) DO UPDATE SET nombre = EXCLUDED.nombre;

-- Reiniciar la secuencia de IDs de mascotas si aplica
SELECT setval('mascotas.mascotas_id_seq', (SELECT MAX(id) FROM mascotas.mascotas));

-- 2. Solicitantes de ejemplo
INSERT INTO adopciones.solicitantes (id, documento, nombre_completo, correo, telefono, direccion, ciudad, tipo_vivienda, tiene_patio) VALUES
(1, '1090123456', 'Carlos Andrés Ramírez', 'carlos.ramirez@gmail.com', '3124567890', 'Av. 4 # 12-40, Barrio San Luis', 'Cúcuta', 'Casa', true),
(2, '1090987654', 'María Fernanda Gómez', 'maria.gomez@hotmail.com', '3187654321', 'Calle 10 # 5-20, Barrio Caobos', 'Cúcuta', 'Apartamento', false),
(3, '1090555444', 'Juan Camilo Torres', 'juan.torres@gmail.com', '3201112233', 'Mz A Lote 3, Urbanización Los Pinos', 'Los Patios', 'Casa', true)
ON CONFLICT (id) DO UPDATE SET nombre_completo = EXCLUDED.nombre_completo;

SELECT setval('adopciones.solicitantes_id_seq', (SELECT MAX(id) FROM adopciones.solicitantes));

-- 3. Solicitudes de adopción de ejemplo
INSERT INTO adopciones.solicitudes (id, mascota_id, solicitante_id, motivo_adopcion, estado, observaciones) VALUES
(1, 5, 1, 'Buscamos un gatito para acompañar a nuestro hijo y brindarle un hogar amoroso.', 'aprobada', 'Visita domiciliaria aprobada. Adopción formalizada con éxito.'),
(2, 4, 2, 'Vivo en apartamento y tengo tiempo para paseos diarios con Bella.', 'pendiente', 'En proceso de verificación de antecedentes y espacio.'),
(3, 1, 3, 'Tenemos finca con amplio espacio cercado para Max.', 'pendiente', 'Solicitud recibida. Pendiente de evaluación.')
ON CONFLICT (id) DO UPDATE SET motivo_adopcion = EXCLUDED.motivo_adopcion;

SELECT setval('adopciones.solicitudes_id_seq', (SELECT MAX(id) FROM adopciones.solicitudes));
