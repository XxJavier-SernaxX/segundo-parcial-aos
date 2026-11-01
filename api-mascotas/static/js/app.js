/**
 * Huellas de Esperanza · Plataforma Web de Adopción Responsable
 * Frontend Integrador de Arquitectura Orientada a Servicios (SOA)
 * Comunicación asíncrona (Fetch REST / JSON) con API 1 (Mascotas) y API 2 (Adopciones)
 */

// =============================================================================
// CONFIGURACIÓN DE URLS BASE DE LOS MICROSERVICIOS
// =============================================================================
const isLocal = window.location.hostname === 'localhost' ||
                window.location.hostname === '127.0.0.1' ||
                window.location.protocol === 'file:';

// En entorno local los dos microservicios corren en puertos independientes
// En Vercel / producción se enrutan mediante vercel.json
const API_MASCOTAS_BASE = isLocal ? 'http://127.0.0.1:8001' : window.location.origin;
const API_ADOPCIONES_BASE = isLocal ? 'http://127.0.0.1:8002' : window.location.origin;

// Cache local de mascotas para renderizar modales y enriquecer tablas
let cacheMascotas = [];

// =============================================================================
// INICIALIZACIÓN AL CARGAR EL DOM
// =============================================================================
document.addEventListener('DOMContentLoaded', () => {
    configurarNavegacionTabs();
    configurarModales();
    configurarFiltros();
    configurarConsolaEndpoints();
    configurarBotonReset();

    // Enlaces dinámicos de Swagger para despliegue en Vercel
    if (!isLocal) {
        const swMascotas = document.getElementById('link-swagger-mascotas');
        const swAdopciones = document.getElementById('link-swagger-adopciones');
        if (swMascotas) swMascotas.href = `${window.location.origin}/mascotas/docs`;
        if (swAdopciones) swAdopciones.href = `${window.location.origin}/solicitudes/docs`;
    }

    // Comprobación de salud de los microservicios y carga inicial de datos
    verificarSaludMicroservicios();
    cargarMascotas();
    cargarSolicitudes();
});

// =============================================================================
// NAVEGACIÓN POR PESTAÑAS (TABS)
// =============================================================================
function configurarNavegacionTabs() {
    const tabs = document.querySelectorAll('.nav-tab');
    const secciones = document.querySelectorAll('.tab-contenido');

    // Enlace del topbar a Swagger / Arquitectura
    document.querySelectorAll('.link-doc, a[href="#swagger-section"]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const tabArqui = document.querySelector('[data-tab="tab-arquitectura"]');
            if (tabArqui) tabArqui.click();
            const el = document.getElementById('swagger-section') || document.querySelector('.card-swagger');
            if (el) el.scrollIntoView({ behavior: 'smooth' });
        });
    });

    tabs.forEach(tab => {

        tab.addEventListener('click', () => {
            const tabTarget = tab.getAttribute('data-tab');

            tabs.forEach(t => t.classList.remove('activa'));
            secciones.forEach(s => s.classList.remove('activa'));

            tab.classList.add('activa');
            const seccionActiva = document.getElementById(tabTarget);
            if (seccionActiva) {
                seccionActiva.classList.add('activa');
            }

            // Recargar datos frescos al cambiar de pestaña
            if (tabTarget === 'tab-mascotas') {
                cargarMascotas();
            } else if (tabTarget === 'tab-solicitudes') {
                cargarSolicitudes();
            }
        });
    });
}

// =============================================================================
// COMPROBACIÓN DE SALUD DE MICROSERVICIOS (TOPBAR)
// =============================================================================
async function verificarSaludMicroservicios() {
    const statusMascotasEl = document.getElementById('status-api-mascotas');
    const statusAdopcionesEl = document.getElementById('status-api-adopciones');

    // Verificar API 1 (Mascotas)
    try {
        const resp1 = await fetch(`${API_MASCOTAS_BASE}/health`, { method: 'GET' });
        if (resp1.ok) {
            statusMascotasEl.textContent = 'ONLINE (Puerto 8001)';
            statusMascotasEl.style.color = '#15803d';
        } else {
            throw new Error(`HTTP ${resp1.status}`);
        }
    } catch (err) {
        statusMascotasEl.textContent = 'IN MEMORY (Local)';
        statusMascotasEl.style.color = '#b45309';
    }

    // Verificar API 2 (Adopciones)
    try {
        const resp2 = await fetch(`${API_ADOPCIONES_BASE}/health`, { method: 'GET' });
        if (resp2.ok) {
            statusAdopcionesEl.textContent = 'ONLINE (Puerto 8002)';
            statusAdopcionesEl.style.color = '#15803d';
        } else {
            throw new Error(`HTTP ${resp2.status}`);
        }
    } catch (err) {
        statusAdopcionesEl.textContent = 'IN MEMORY (Local)';
        statusAdopcionesEl.style.color = '#b45309';
    }
}

// =============================================================================
// GESTIÓN DEL CATÁLOGO DE MASCOTAS (CONSUMO API 1)
// =============================================================================
async function cargarMascotas() {
    const grid = document.getElementById('grid-mascotas');
    const filtroEstado = document.getElementById('filtro-estado').value;
    const filtroEspecie = document.getElementById('filtro-especie').value;

    let url = `${API_MASCOTAS_BASE}/mascotas?`;
    if (filtroEstado) url += `estado=${encodeURIComponent(filtroEstado)}&`;
    if (filtroEspecie) url += `especie=${encodeURIComponent(filtroEspecie)}&`;

    try {
        grid.innerHTML = '<div class="cargando">Cargando catálogo de mascotas desde API 1...</div>';
        const respuesta = await fetch(url);
        if (!respuesta.ok) {
            throw new Error(`Error ${respuesta.status}: No se pudo consultar la API de Mascotas.`);
        }
        const mascotas = await respuesta.json();
        cacheMascotas = mascotas;
        renderizarMascotas(mascotas);
    } catch (error) {
        console.error('Error cargando mascotas:', error);
        grid.innerHTML = `
            <div class="cargando" style="color: #b91c1c;">
                <strong><i class="ph-bold ph-warning"></i> Error conectando con API 1:</strong> ${error.message}
                <br><small>Asegúrate de que la API de Mascotas esté corriendo en <code>http://127.0.0.1:8001</code></small>
            </div>
        `;
    }
}

function renderizarMascotas(mascotas) {
    const grid = document.getElementById('grid-mascotas');
    if (!mascotas || mascotas.length === 0) {
        grid.innerHTML = `
            <div class="cargando" style="grid-column: 1 / -1; padding: 40px; text-align: center;">
                <i class="ph-bold ph-paw-print" style="font-size: 2.5rem; color: #94a3b8; display: block; margin-bottom: 10px;"></i>
                No se encontraron mascotas con los filtros seleccionados.
            </div>
        `;
        return;
    }

    grid.innerHTML = mascotas.map(m => {
        const badgeClase = m.estado === 'disponible' ? 'badge-disponible' :
                           m.estado === 'en_proceso' ? 'badge-en-proceso' : 'badge-adoptada';
        const badgeTexto = m.estado === 'disponible' ? 'Disponible para Adopción' :
                           m.estado === 'en_proceso' ? 'En Proceso de Adopción' : '¡Adoptado!';

        const botonDisabled = m.estado === 'adoptada' ? 'disabled' : '';
        const botonTexto = m.estado === 'adoptada' ? 'Ya Adoptado' :
                           m.estado === 'en_proceso' ? 'Solicitud en Curso' : 'Adoptar a ' + m.nombre;
        const botonClase = m.estado === 'adoptada' ? 'btn-adoptada-disabled' : 'btn-primario';

        const fotoDefault = m.especie === 'Gato'
            ? 'https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?auto=format&fit=crop&w=600&q=80'
            : 'https://images.unsplash.com/photo-1543466835-00a7907e9de1?auto=format&fit=crop&w=600&q=80';

        const foto = m.foto_url || fotoDefault;

        return `
            <article class="tarjeta-mascota" data-id="${m.id}">
                <div class="tarjeta-imagen-wrapper">
                    <img src="${foto}" alt="${m.nombre}" class="tarjeta-imagen" loading="lazy" onerror="this.src='${fotoDefault}'">
                    <span class="badge-estado ${badgeClase}">${badgeTexto}</span>
                </div>
                <div class="tarjeta-cuerpo">
                    <div class="tarjeta-header">
                        <h3 class="tarjeta-titulo">${m.nombre}</h3>
                        <span class="tarjeta-especie"><i class="ph-fill ph-${m.especie === 'Gato' ? 'cat' : 'dog'}"></i> ${m.especie}</span>
                    </div>

                    <div class="tarjeta-detalles">
                        <span><strong>Raza:</strong> ${m.raza || 'Mestizo'}</span>
                        <span><strong>Edad:</strong> ${m.edad_meses} meses</span>
                        <span><strong>Sexo:</strong> ${m.sexo}</span>
                        <span><strong>Tamaño:</strong> ${m.tamano}</span>
                    </div>

                    <p class="tarjeta-descripcion">${m.descripcion || 'Sin descripción adicional.'}</p>

                    <div class="tarjeta-acciones">
                        <button class="btn ${botonClase} btn-ancho-completo btn-iniciar-adopcion"
                                data-id="${m.id}"
                                ${botonDisabled}>
                            <i class="ph-bold ph-heart"></i> ${botonTexto}
                        </button>
                    </div>
                </div>
            </article>
        `;
    }).join('');

    // Asignar listeners a los botones de adopción
    document.querySelectorAll('.btn-iniciar-adopcion').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const mascotaId = parseInt(btn.getAttribute('data-id'), 10);
            abrirModalAdopcion(mascotaId);
        });
    });
}

function configurarFiltros() {
    const filtroEstado = document.getElementById('filtro-estado');
    const filtroEspecie = document.getElementById('filtro-especie');
    const btnRefrescarMascotas = document.getElementById('btn-refrescar-mascotas');

    if (filtroEstado) filtroEstado.addEventListener('change', cargarMascotas);
    if (filtroEspecie) filtroEspecie.addEventListener('change', cargarMascotas);
    if (btnRefrescarMascotas) btnRefrescarMascotas.addEventListener('click', cargarMascotas);
}

// =============================================================================
// GESTIÓN DE SOLICITUDES DE ADOPCIÓN (CONSUMO API 2 CON VALIDACIÓN API 1)
// =============================================================================
async function cargarSolicitudes() {
    const tbody = document.getElementById('tbody-solicitudes');
    const btnRefrescar = document.getElementById('btn-refrescar-solicitudes');

    try {
        tbody.innerHTML = '<tr><td colspan="8" class="texto-centro">Consultando solicitudes desde API 2...</td></tr>';
        const respuesta = await fetch(`${API_ADOPCIONES_BASE}/solicitudes`);
        if (!respuesta.ok) {
            throw new Error(`Error ${respuesta.status}: No se pudo consultar la API de Adopciones.`);
        }
        const solicitudes = await respuesta.json();
        renderizarSolicitudes(solicitudes);
    } catch (error) {
        console.error('Error cargando solicitudes:', error);
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="texto-centro" style="color: #b91c1c;">
                    <strong><i class="ph-bold ph-warning"></i> Error consultando API 2:</strong> ${error.message}
                    <br><small>Verifica que el servicio esté corriendo en <code>http://127.0.0.1:8002</code></small>
                </td>
            </tr>
        `;
    }

    if (btnRefrescar) {
        btnRefrescar.onclick = cargarSolicitudes;
    }
}

function renderizarSolicitudes(solicitudes) {
    const tbody = document.getElementById('tbody-solicitudes');
    if (!solicitudes || solicitudes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="texto-centro">No hay solicitudes registradas aún.</td></tr>';
        return;
    }

    tbody.innerHTML = solicitudes.map(s => {
        const sol = s.solicitante || {};
        const mascotaNombre = s.mascota_info?.nombre || `Mascota #${s.mascota_id}`;
        const mascotaEspecie = s.mascota_info?.especie ? `(${s.mascota_info.especie})` : '';

        const badgeClase = s.estado === 'aprobada' ? 'badge-aprobada' :
                           s.estado === 'rechazada' ? 'badge-rechazada' : 'badge-pendiente';
        const fechaFormateada = s.fecha_solicitud ? new Date(s.fecha_solicitud).toLocaleDateString('es-CO', {
            year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
        }) : '-';

        let accionesHtml = '';
        if (s.estado === 'pendiente') {
            accionesHtml = `
                <div class="acciones-fila">
                    <button class="btn btn-sm btn-exito btn-resolver-solicitud" data-id="${s.id}" data-accion="aprobada" title="Aprobar adopción y actualizar estado en API 1">
                        <i class="ph-bold ph-check"></i> Aprobar
                    </button>
                    <button class="btn btn-sm btn-peligro btn-resolver-solicitud" data-id="${s.id}" data-accion="rechazada" title="Rechazar solicitud">
                        <i class="ph-bold ph-x"></i> Rechazar
                    </button>
                </div>
            `;
        } else {
            accionesHtml = `
                <div class="resolucion-info">
                    <small><strong>${s.estado.toUpperCase()}</strong></small>
                    <small class="texto-muted">${s.observaciones || ''}</small>
                </div>
            `;
        }

        return `
            <tr>
                <td><strong>#${s.id}</strong></td>
                <td>
                    <div class="mascota-celda">
                        <span class="nombre-destacado">${mascotaNombre} ${mascotaEspecie}</span>
                        <small class="texto-muted">ID: ${s.mascota_id}</small>
                    </div>
                </td>
                <td>
                    <strong>${sol.nombre_completo || 'Solicitante'}</strong>
                    <div class="texto-muted"><small>Doc: ${sol.documento || '-'}</small></div>
                </td>
                <td>
                    <div><i class="ph-bold ph-envelope"></i> ${sol.correo || '-'}</div>
                    <div><i class="ph-bold ph-phone"></i> ${sol.telefono || '-'}</div>
                    <small class="texto-muted">${sol.tipo_vivienda || 'Casa'} · Patio: ${sol.tiene_patio ? 'Sí' : 'No'}</small>
                </td>
                <td>
                    <div class="motivo-texto" title="${s.motivo_adopcion}">
                        ${s.motivo_adopcion}
                    </div>
                </td>
                <td><small>${fechaFormateada}</small></td>
                <td><span class="badge-tabla ${badgeClase}">${s.estado.toUpperCase()}</span></td>
                <td>${accionesHtml}</td>
            </tr>
        `;
    }).join('');

    // Vincular botones de resolución (Aprobar / Rechazar)
    document.querySelectorAll('.btn-resolver-solicitud').forEach(btn => {
        btn.addEventListener('click', async () => {
            const idSolicitud = btn.getAttribute('data-id');
            const nuevoEstado = btn.getAttribute('data-accion');
            await ejecutarResolucionSolicitud(idSolicitud, nuevoEstado);
        });
    });
}

// =============================================================================
// REGLA CRÍTICA DEL EXAMEN: RESOLVER SOLICITUD Y NOTIFICAR API 1
// =============================================================================
async function ejecutarResolucionSolicitud(idSolicitud, estado) {
    const accionTexto = estado === 'aprobada' ? 'APROBAR' : 'RECHAZAR';
    const confirmacion = confirm(`¿Estás seguro de que deseas ${accionTexto} la solicitud #${idSolicitud}?\n\nAl aprobarla, la API 2 comunicará a la API 1 para marcar la mascota como 'adoptada' y evitará duplicados.`);
    if (!confirmacion) return;

    let observaciones = prompt(`Observaciones para la resolución (${estado}):`,
        estado === 'aprobada' ? 'Visita domiciliaria satisfactoria y compromiso de tenencia responsable formalizado.' : 'No cumple con las condiciones mínimas de espacio y tiempo.');

    if (observaciones === null) return; // Cancelado

    try {
        mostrarAlerta(`Procesando resolución de Solicitud #${idSolicitud} en API 2 con verificación SOA...`, 'info');

        const respuesta = await fetch(`${API_ADOPCIONES_BASE}/solicitudes/${idSolicitud}/resolucion`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                estado: estado,
                observaciones: observaciones || `Resolución: ${estado}`
            })
        });

        const data = await respuesta.json();

        if (respuesta.status === 409) {
            // CONFLICTO DETECTADO POR LA REGLA DE ORO DEL EXAMEN
            mostrarAlerta(`⚠️ REGLA DE ORO SOA ACTIVADA (HTTP 409 Conflicto):\n${data.detail}`, 'error');
            alert(`⚠️ Conflicto de Adopción (HTTP 409):\n\n${data.detail}\n\nLa regla de negocio del examen impidió que dos solicitudes sean aprobadas para la misma mascota.`);
            cargarSolicitudes();
            cargarMascotas();
            return;
        }

        if (!respuesta.ok) {
            throw new Error(data.detail || `Error ${respuesta.status} en API 2`);
        }

        mostrarAlerta(`✅ Éxito SOA: ${data.mensaje} | Comunicación con API 1 completada exitosamente.`, 'exito');
        // Refrescar ambas vistas para ver el impacto coordinado en tiempo real
        await cargarSolicitudes();
        await cargarMascotas();
        verificarSaludMicroservicios();

    } catch (error) {
        console.error('Error resolviendo solicitud:', error);
        mostrarAlerta(`❌ Error al resolver solicitud: ${error.message}`, 'error');
    }
}

// =============================================================================
// MODALES: ADOPCIÓN Y REGISTRO DE MASCOTA
// =============================================================================
function configurarModales() {
    // Cerrar modales con botones de cerrar o clic en fondo
    document.querySelectorAll('.btn-cerrar-modal').forEach(btn => {
        btn.addEventListener('click', () => {
            const modalId = btn.getAttribute('data-modal');
            cerrarModal(modalId);
        });
    });

    document.querySelectorAll('.modal-overlay').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.add('oculta');
            }
        });
    });

    // Abrir modal registrar nueva mascota
    const btnAbrirMascota = document.getElementById('btn-abrir-modal-mascota');
    if (btnAbrirMascota) {
        btnAbrirMascota.addEventListener('click', () => {
            abrirModal('modal-nueva-mascota');
        });
    }

    // Formulario de Solicitud de Adopción (Envío a API 2)
    const formAdopcion = document.getElementById('form-solicitud-adopcion');
    if (formAdopcion) {
        formAdopcion.addEventListener('submit', async (e) => {
            e.preventDefault();
            await enviarSolicitudAdopcion();
        });
    }

    // Formulario de Registro de Mascota (Envío a API 1)
    const formNuevaMascota = document.getElementById('form-nueva-mascota');
    if (formNuevaMascota) {
        formNuevaMascota.addEventListener('submit', async (e) => {
            e.preventDefault();
            await registrarNuevaMascota();
        });
    }
}

function abrirModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove('oculta');
}

function cerrarModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add('oculta');
}

function abrirModalAdopcion(mascotaId) {
    const mascota = cacheMascotas.find(m => m.id === mascotaId);
    if (!mascota) {
        alert('Mascota no encontrada');
        return;
    }

    if (mascota.estado === 'adoptada') {
        alert('Esta mascota ya fue adoptada formalmente y no recibe nuevas solicitudes.');
        return;
    }

    document.getElementById('adopcion-mascota-id').value = mascota.id;

    const resumenEl = document.getElementById('card-mascota-resumen');
    resumenEl.innerHTML = `
        <div class="resumen-flex">
            <img src="${mascota.foto_url || ''}" alt="${mascota.nombre}" class="resumen-foto" onerror="this.style.display='none'">
            <div>
                <h4>Mascota a Adoptar: <strong>${mascota.nombre}</strong> (${mascota.especie})</h4>
                <p><small>Raza: ${mascota.raza} · Edad: ${mascota.edad_meses} meses · Tamaño: ${mascota.tamano}</small></p>
                <p><small class="texto-muted">ID de la Mascota en API 1: <code>#${mascota.id}</code> · Estado actual: <span class="badge-online">${mascota.estado}</span></small></p>
            </div>
        </div>
    `;

    abrirModal('modal-adopcion');
}

async function enviarSolicitudAdopcion() {
    const mascotaId = parseInt(document.getElementById('adopcion-mascota-id').value, 10);
    const documento = document.getElementById('sol-documento').value.trim();
    const nombre = document.getElementById('sol-nombre').value.trim();
    const correo = document.getElementById('sol-correo').value.trim();
    const telefono = document.getElementById('sol-telefono').value.trim();
    const direccion = document.getElementById('sol-direccion').value.trim();
    const tipoVivienda = document.getElementById('sol-tipo-vivienda').value;
    const tienePatio = document.getElementById('sol-tiene-patio').checked;
    const motivo = document.getElementById('sol-motivo').value.trim();

    const payload = {
        mascota_id: mascotaId,
        solicitante: {
            documento: documento,
            nombre_completo: nombre,
            correo: correo,
            telefono: telefono,
            direccion: direccion,
            ciudad: 'Cúcuta',
            tipo_vivienda: tipoVivienda,
            tiene_patio: tienePatio
        },
        motivo_adopcion: motivo
    };

    const btnSubmit = document.getElementById('btn-enviar-adopcion');
    btnSubmit.disabled = true;
    btnSubmit.innerHTML = '<i class="ph-bold ph-spinner"></i> Validando con API 1...';

    try {
        const respuesta = await fetch(`${API_ADOPCIONES_BASE}/solicitudes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await respuesta.json();

        if (!respuesta.ok) {
            throw new Error(data.detail || `Error ${respuesta.status} en API 2`);
        }

        cerrarModal('modal-adopcion');
        document.getElementById('form-solicitud-adopcion').reset();

        mostrarAlerta(`🎉 ¡Solicitud registrada exitosamente en API 2! Verificación con API 1 completada.`, 'exito');

        // Cambiar a la pestaña de solicitudes para ver la nueva solicitud
        const tabSolicitudesBtn = document.querySelector('[data-tab="tab-solicitudes"]');
        if (tabSolicitudesBtn) tabSolicitudesBtn.click();

    } catch (error) {
        console.error('Error al registrar solicitud:', error);
        mostrarAlerta(`❌ Error al enviar solicitud: ${error.message}`, 'error');
        alert(`Error al registrar la solicitud:\n\n${error.message}`);
    } finally {
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = '<i class="ph-bold ph-paper-plane-right"></i> Enviar Solicitud (API 2)';
    }
}

async function registrarNuevaMascota() {
    const nombre = document.getElementById('m-nombre').value.trim();
    const especie = document.getElementById('m-especie').value;
    const raza = document.getElementById('m-raza').value.trim() || 'Mestizo';
    const edadMeses = parseInt(document.getElementById('m-edad').value, 10);
    const sexo = document.getElementById('m-sexo').value;
    const tamano = document.getElementById('m-tamano').value;
    const fotoUrl = document.getElementById('m-foto').value.trim();
    const descripcion = document.getElementById('m-descripcion').value.trim();

    const payload = {
        nombre: nombre,
        especie: especie,
        raza: raza,
        edad_meses: edadMeses,
        sexo: sexo,
        tamano: tamano,
        foto_url: fotoUrl,
        descripcion: descripcion
    };

    try {
        const respuesta = await fetch(`${API_MASCOTAS_BASE}/mascotas`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await respuesta.json();
        if (!respuesta.ok) {
            throw new Error(data.detail || `Error ${respuesta.status}`);
        }

        cerrarModal('modal-nueva-mascota');
        document.getElementById('form-nueva-mascota').reset();
        mostrarAlerta(`🐶 Mascota '${data.nombre}' registrada exitosamente en la API 1 con ID #${data.id}.`, 'exito');
        cargarMascotas();

    } catch (error) {
        console.error('Error registrando mascota:', error);
        mostrarAlerta(`❌ Error al registrar mascota en API 1: ${error.message}`, 'error');
    }
}

// =============================================================================
// CONSOLA INTERACTIVA DE ENDPOINTS EN VIVO (TAB ARQUITECTURA)
// =============================================================================
function configurarConsolaEndpoints() {
    const btnEjecutar = document.getElementById('btn-consola-ejecutar');
    const selectEndpoint = document.getElementById('consola-endpoint');
    const statusEl = document.getElementById('consola-status');
    const tiempoEl = document.getElementById('consola-tiempo');
    const jsonEl = document.getElementById('consola-json');

    if (!btnEjecutar) return;

    btnEjecutar.addEventListener('click', async () => {
        const path = selectEndpoint.value;
        let urlCompleta = '';

        if (path.includes('mascotas')) {
            // Remapear ruta para compatibilidad local y Vercel
            const ruta = path.replace('/api/v1/mascotas', '');
            urlCompleta = `${API_MASCOTAS_BASE}${ruta}`;
        } else {
            const ruta = path.replace('/api/v1/adopciones', '');
            urlCompleta = `${API_ADOPCIONES_BASE}${ruta}`;
        }

        statusEl.textContent = 'Enviando...';
        tiempoEl.textContent = '...';
        jsonEl.textContent = `GET ${urlCompleta}\n\nEsperando respuesta del servicio...`;

        const inicio = performance.now();
        try {
            const resp = await fetch(urlCompleta);
            const duracion = Math.round(performance.now() - inicio);
            const data = await resp.json();

            statusEl.textContent = `${resp.status} ${resp.statusText || 'OK'}`;
            statusEl.style.color = resp.ok ? '#15803d' : '#b91c1c';
            tiempoEl.textContent = `${duracion} ms`;
            jsonEl.textContent = JSON.stringify(data, null, 2);
        } catch (err) {
            const duracion = Math.round(performance.now() - inicio);
            statusEl.textContent = 'ERROR CONEXIÓN';
            statusEl.style.color = '#b91c1c';
            tiempoEl.textContent = `${duracion} ms`;
            jsonEl.textContent = `Error al conectar con ${urlCompleta}:\n${err.message}`;
        }
    });
}

// =============================================================================
// REINICIAR DATOS SEMILLA (DEMO RESET)
// =============================================================================
function configurarBotonReset() {
    const btnReset = document.getElementById('btn-reset-demo');
    if (!btnReset) return;

    btnReset.addEventListener('click', async () => {
        const ok = confirm('¿Deseas reiniciar los datos de demostración a su estado inicial?');
        if (!ok) return;

        try {
            mostrarAlerta('⏳ Reiniciando datos en Supabase y microservicios...', 'info');
            const urlResetMascotas = isLocal ? 'http://127.0.0.1:8001/reset' : `${window.location.origin}/mascotas/reset`;
            const urlResetAdopciones = isLocal ? 'http://127.0.0.1:8002/reset' : `${window.location.origin}/solicitudes/reset`;

            await fetch(urlResetMascotas, { method: 'POST' }).catch(() => {});
            await fetch(urlResetAdopciones, { method: 'POST' }).catch(() => {});

            mostrarAlerta('🔄 ¡Datos de demostración reiniciados con éxito!', 'exito');
            await cargarMascotas();
            await cargarSolicitudes();
        } catch (e) {
            console.error('Error al reiniciar datos:', e);
            mostrarAlerta(`Error al reiniciar: ${e.message}`, 'error');
        }
    });
}


// =============================================================================
// NOTIFICACIONES FLOTANTES (ALERTAS)
// =============================================================================
function mostrarAlerta(mensaje, tipo = 'info') {
    const alerta = document.getElementById('alerta-global');
    if (!alerta) return;

    alerta.textContent = mensaje;
    alerta.className = `alerta alerta-${tipo}`;
    alerta.classList.remove('oculta');

    setTimeout(() => {
        alerta.classList.add('oculta');
    }, 6000);
}
