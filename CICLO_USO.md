# Locks Manager — Documentación Completa
## PHA Hotel · Saflok Model 790
**Versión:** Abril 2026

---

## Índice

1. [Descripción general](#1-descripción-general)
2. [Arquitectura técnica](#2-arquitectura-técnica)
3. [Iniciar el sistema](#3-iniciar-el-sistema)
4. [Módulo: Dashboard](#4-módulo-dashboard)
5. [Módulo: Cerraduras](#5-módulo-cerraduras)
6. [Módulo: Mantenimiento](#6-módulo-mantenimiento)
7. [Módulo: Baterías](#7-módulo-baterías)
8. [Módulo: Reportes](#8-módulo-reportes)
9. [Módulo: Sectores](#9-módulo-sectores)
10. [Módulo: Historial](#10-módulo-historial)
11. [Administración de usuarios](#11-administración-de-usuarios)
12. [Respaldos](#12-respaldos)
13. [Configuración avanzada](#13-configuración-avanzada)
14. [Resolución de problemas](#14-resolución-de-problemas)
15. [Glosario](#15-glosario)

---

## 1. Descripción general

**Locks Manager** es una aplicación web interna desarrollada para el PHA Hotel para gestionar el mantenimiento preventivo y correctivo de las cerraduras electrónicas **Saflok Model 790** instaladas en habitaciones, salones y áreas comunes.

### Qué resuelve

Antes del sistema, el técnico anotaba manualmente en papel: número de habitación, hora, fecha, estado de la cerradura y observaciones. Esto dificultaba el seguimiento histórico, la generación de reportes y la detección de problemas recurrentes.

Locks Manager centraliza toda esa información y automatiza:
- Registro de mantenimientos con fecha, hora y técnico automáticos
- Cálculo de nivel de batería a partir del voltaje medido
- Generación del reporte oficial Excel `SIS.PHA.REG.026`
- Alertas de baterías bajas y cerraduras sin revisión reciente
- Gráficas de progreso por sector y trimestre

### Estructura del hotel registrada

| Sector | Código | Habitaciones | Trimestres asignados |
|--------|--------|-------------|---------------------|
| Sector Cien | 100 | 101–120 (18 activas) | Q1, Q3 |
| Sector Docientos | 200 | 201–225 (24 activas) | Q2, Q4 |
| Sector Trecientos | 300 | 305–316 (10 activas) | Q1, Q3 |
| Sector Cuatrocientos | 400 | 401–423 (22 activas) | Q2, Q4 |
| Sector Quinientos + Salones | 500 | 501–537 + SL1-3, SOB, SCU, SDL, SDB, SDP, GYM, P500 | Q2, Q4 |

> Los trimestres determinan qué cerraduras aparecen en la lista de mantenimiento de cada período. Si una cerradura no aparece, verifica los trimestres de su sector en **Configuración → Sectores**.

---

## 2. Arquitectura técnica

```
Locks Manager/
├── app.py                  ← Punto de entrada Flask (factory pattern)
├── config.py               ← Configuración global (BD, baterías, usuarios, supervisor)
├── database.py             ← Helpers de acceso a SQL Server
├── routes/
│   ├── auth.py             ← Login / logout
│   ├── admin.py            ← Gestión de usuarios (solo admin)
│   ├── dashboard.py        ← Estadísticas y gráficas del dashboard
│   ├── locks.py            ← CRUD de cerraduras, eventos, clock config
│   ├── maintenance.py      ← CRUD mantenimiento + historial
│   ├── batteries.py        ← Lecturas de batería, alertas, stats
│   ├── reports.py          ← Generación de Excel
│   └── sectors.py          ← CRUD de sectores y trimestres
├── templates/              ← Plantillas Jinja2 (HTML)
├── static/                 ← CSS y JS globales
└── scripts de utilidad:
    ├── init_db.py          ← Crear BD desde cero (ejecutar solo una vez)
    ├── import_excel.py     ← Importar historial desde Excel antiguo
    ├── add_users_table.py  ← Migración: crear tabla de usuarios (ya ejecutado)
    ├── export_mantos.py    ← Respaldo solo de mantenimientos
    └── backup_db.py        ← Respaldo completo de toda la BD
```

**Stack tecnológico:**
- Backend: Python 3 + Flask 3
- Base de datos: SQL Server (ODBC Driver 17) — BD: `LockManager`
- Frontend: HTML/CSS/JS puro (sin frameworks externos excepto Chart.js)
- Reportes: openpyxl

---

## 3. Iniciar el sistema

### Inicio rápido
1. Doble clic en `start.bat`
2. El servidor inicia en `http://localhost:5000`
3. El navegador se abre automáticamente

### Inicio manual (alternativo)
```
python app.py
```

### Iniciar sesión
Al abrir la app aparece la pantalla de login. Ingresa tu usuario y contraseña asignados.

- La sesión dura **7 días** — no necesitas volver a ingresar a menos que hagas clic en "Salir"
- Tu nombre aparece automáticamente en el campo **Técnico** al registrar mantenimientos
- Si olvidas tu contraseña, pide al administrador que la cambie en **Admin → Usuarios**

### Detener el servidor
Cierra la ventana de la terminal donde corre el servidor, o presiona `Ctrl + C` en ella.

---

## 4. Módulo: Dashboard

**Acceso:** `/` — Página principal al iniciar sesión

### Qué muestra

**Tarjetas de estadísticas (fila superior):**
- Cerraduras activas / inactivas
- Eventos abiertos sin resolver
- % de mantenimiento completado en el trimestre actual
- Cantidad de cerraduras con batería baja (<25%)

**Gráficas:**
1. **Progreso por Sector (Q actual)** — Barras horizontales comparando cerraduras realizadas vs programadas por sector
2. **Distribución de Baterías** — Dona con 4 niveles: Buena ≥75% / Media 25–74% / Baja 10–24% / Crítica <10%
3. **Historial Trimestral** — Barras de mantenimientos realizados vs total en los últimos 4–6 trimestres

**Alertas de batería baja:** tabla con las cerraduras por debajo del 25%, ordenadas de menor a mayor.

**Mantenimientos recientes:** últimos 10 registros guardados en cualquier trimestre.

---

## 5. Módulo: Cerraduras

**Acceso:** Sidebar → 🔒 Cerraduras (`/locks/`)

### Listado
- Muestra todas las cerraduras con: sector, código, último % de batería, última fecha de manto, eventos abiertos
- Filtros: por sector, por estado (activa/inactiva), búsqueda por número/nombre
- Clic en el número de habitación → vista de detalle

### Agregar cerradura nueva
Sidebar → ➕ Nueva Cerradura (`/locks/add`)
- Campos: sector, código de habitación, nombre descriptivo (opcional), modelo, número de serie, fecha de instalación, notas
- No se permiten códigos duplicados dentro del mismo sector

### Detalle de cerradura
Muestra 4 pestañas:

**🔧 Mantenimientos** — historial completo de todos los registros de manto para esa cerradura
- Botón ✏️ para editar cualquier registro
- Botón 🗑 para eliminar un registro (con confirmación)
- Esta es la única forma de editar/borrar un manto que NO está en el trimestre actual de la lista

**🔋 Historial Batería** — todas las lecturas de voltaje registradas
- Gráfico de línea mostrando la tendencia del nivel de batería
- Puntos azules = lectura donde se cambiaron las baterías
- Botón 🗑 para eliminar lecturas registradas por error

**⚠️ Eventos** — incidentes reportados (falla, reparación, inspección, etc.)
- Botón "✓ Resolver" para cerrar un evento abierto
- Modal para agregar nuevo evento

**⏰ Config. Reloj** — historial de configuraciones de reloj de la cerradura

---

## 6. Módulo: Mantenimiento

**Acceso:** Sidebar → 🔧 Mantenimiento (`/maintenance/`)

### Vista por Trimestre (principal)

La tabla muestra **todas las cerraduras programadas** para el trimestre y año seleccionados. Solo aparecen las cerraduras cuyos sectores tienen ese trimestre asignado.

**Filtros disponibles:** Trimestre (Q1–Q4), Año, Sector

**Edición inline:** puedes modificar directamente en la tabla:
- Fecha de mantenimiento
- Hora
- Técnico
- Supervisor
- Estado (Realizado / Pendiente / Pospuesto)
- Anotaciones

**Guardar Todo:** al presionar 💾 Guardar Todo, aparece una confirmación con el número de registros a guardar. Solo guarda las filas que tienen un estado seleccionado.

**Botón 📋:** abre el formulario detallado de esa cerradura para ese trimestre.

### Formulario individual de mantenimiento

**Acceso:** Topbar → 🔧 Registrar, o desde el detalle de cerradura

**Campos automáticos:**
- **Trimestre y Año** → se establecen en el trimestre actual (editables)
- **Fecha** → fecha de hoy (editable)
- **Hora** → hora actual (editable)
- **Técnico** → nombre del usuario logueado (editable)
- **Supervisado por** → "MB" por defecto (editable)

**Selector de habitación:**
- Escribe el número de la habitación para filtrar la lista
- También puedes desplazarte por todas las habitaciones disponibles
- Al seleccionar una cerradura con historial de batería, aparece la **última lectura registrada** (voltaje, %, días transcurridos, técnico que la registró)

**Sección de Batería (integrada):**
- Ingresa el voltaje medido → el % se calcula automáticamente en tiempo real
- Marca el checkbox si se cambiaron las baterías durante este mantenimiento
- **Al guardar el formulario, la lectura de batería se guarda automáticamente** en el módulo de Baterías — no necesitas ir a otro lado

### Historial Completo

**Acceso:** Sidebar → 📋 Historial (`/maintenance/history`)

Muestra **todos los registros de mantenimiento** sin restricción de trimestre/sector programado. Útil para:
- Auditoría de registros
- Buscar un manto registrado en el trimestre incorrecto
- Filtrar por técnico, estado, sector o fecha

Desde aquí también puedes editar o eliminar cualquier registro.

### Editar o eliminar un manto registrado por error

**Si la cerradura sí aparece en la lista del trimestre:**
- Modifica directamente en la tabla y presiona Guardar Todo
- O usa el botón 📋 para ir al formulario completo

**Si la cerradura NO aparece en la lista** (sector no programado para ese Q):
1. Ve a **Cerraduras** → busca la cerradura → clic en el número
2. Pestaña **🔧 Mantenimientos**
3. Botón ✏️ para editar, 🗑 para eliminar

---

## 7. Módulo: Baterías

**Acceso:** Sidebar → 🔋 Baterías (`/batteries/`)

### Cómo funciona el cálculo de batería

Las cerraduras usan **3 baterías AA en serie**:
- Voltaje máximo (baterías nuevas): **4.5V = 100%**
- Voltaje mínimo (baterías agotadas): **2.7V = 0%**
- Fórmula: `% = (voltaje - 2.7) / (4.5 - 2.7) × 100`
- Alerta automática: **< 25%** (aprox. 3.06V)

### Tarjetas de estadísticas

| Tarjeta | Descripción |
|---------|-------------|
| Promedio General | % promedio de todas las cerraduras con lectura |
| Batería Baja | Cerraduras con % < 25% |
| Crítico | Cerraduras con % < 10% (cambio inmediato) |
| Vida Prom. Batería | Días promedio entre cambios (calculado de historial) |
| Sin Lectura | Cerraduras que nunca han tenido una lectura |
| Sin Lectura Reciente | Cerraduras sin medición en los últimos 90 días |

### Gráfica de promedio por sector
Barras mostrando el voltaje promedio por sector. Color verde ≥75%, amarillo 25–74%, rojo <25%.

### Filtros

- **Por sector:** solo muestra las cerraduras de ese sector
- **Solo alertas:** filtra cerraduras con batería < 25%
- **Sin lectura reciente (+90d):** filtra cerraduras desactualizadas

### Registrar batería por separado

**Ruta recomendada:** durante el mantenimiento (sección batería en el formulario de manto).

**Ruta alternativa:** Sidebar → 📝 Log Batería o botón "+ Log" en la tabla

1. Seleccionar habitación
2. Ingresar voltaje medido con el multímetro
3. El % aparece en tiempo real
4. Marcar si se cambiaron las baterías
5. Guardar

### Eliminar lectura de batería errónea

1. Ve al **detalle de la cerradura** (Cerraduras → clic en la habitación)
2. Pestaña **🔋 Historial Batería**
3. Botón 🗑 en la lectura incorrecta (con confirmación)

---

## 8. Módulo: Reportes

**Acceso:** Sidebar → 📄 Reportes (`/reports/`)

### Reporte de Mantenimiento (Excel)

Genera el archivo Excel con formato oficial **SIS.PHA.REG.026**.
- Selecciona Trimestre y Año
- El archivo descarga con nombre: `SIS.PHA.REG.026_QX_YYYY.xlsx`
- Contiene **2 hojas:**
  - **T1:** Sectores 100, 200, 300
  - **T2:** Sectores 400, 500
- Replica exactamente el formato del documento original: encabezado con logo, columnas, bordes, estilos

### Reporte de Baterías (Excel)

Exporta el estado actual de todas las baterías: sector, habitación, voltaje, %, si se cambiaron, técnico y fecha de última lectura.

---

## 9. Módulo: Sectores

**Acceso:** Sidebar → 🏨 Sectores (`/sectors/`)

### Qué se gestiona aquí

- Nombre y descripción de cada sector
- **Trimestres asignados (Q1–Q4):** determinan cuándo aparece cada sector en la lista de mantenimiento

> **Importante:** si cambias los trimestres de un sector, las cerraduras de ese sector solo aparecerán en la lista de los nuevos trimestres configurados. Los registros históricos no se modifican.

### Activar / desactivar sector

Un sector inactivo no aparece en los listados ni en los filtros. Las cerraduras de ese sector permanecen en la BD pero no se muestran.

---

## 10. Módulo: Historial

**Acceso:** Sidebar → 📋 Historial (`/maintenance/history`)

Vista de auditoría sin restricciones. Muestra TODOS los registros de mantenimiento con filtros por:
- Año
- Trimestre
- Sector
- Estado
- Técnico (búsqueda parcial)

Desde aquí puedes editar o eliminar cualquier registro, sin importar si la cerradura está o no programada para ese trimestre.

---

## 11. Administración de usuarios

**Acceso:** Sidebar → 👥 Usuarios (solo visible para administradores) (`/admin/users`)

### Roles disponibles

| Rol | Acceso |
|-----|--------|
| `technician` | Todas las funciones del sistema excepto gestión de usuarios |
| `admin` | Todo lo anterior + gestión de usuarios |

### Agregar usuario

1. Clic en "➕ Nuevo Usuario"
2. Completar: usuario (login), contraseña, nombre completo, rol
3. El nombre completo se usa para auto-llenar el campo "Técnico" en los formularios

### Editar usuario

- Botón ✏️ → actualiza nombre, rol o contraseña
- Dejar contraseña en blanco = no cambia la contraseña actual

### Activar / desactivar usuario

- Botón 🔴 → desactiva (no puede iniciar sesión)
- Botón 🟢 → reactiva
- No puedes desactivar tu propia cuenta

### Cambiar el supervisor por defecto

Edita `config.py` y cambia:
```python
DEFAULT_SUPERVISOR = 'MB'
```
Reinicia el servidor para que tome efecto.

---

## 12. Respaldos

### Respaldo completo de la BD
```
python backup_db.py
```
Exporta todas las tablas a Excel: `backup_BD_completo_YYYYMMDD_HHMMSS.xlsx`

### Respaldo solo de mantenimientos
```
python export_mantos.py
```
Exporta solo `maintenance_records` a Excel: `backup_mantos_YYYYMMDD_HHMMSS.xlsx`

### Recomendación
Ejecutar `backup_db.py` **antes de cualquier cambio importante** en la BD o actualización del software.

Los archivos de respaldo se generan en la misma carpeta del proyecto.

---

## 13. Configuración avanzada

### Archivo `config.py`

```python
# Contraseñas y nombre de usuarios
USERS = {
    'admin':   {'password': 'admin',  'full_name': 'Administrador'},
    'diego':   {'password': 'diego',  'full_name': 'Diego Andrino'},
}
# Nota: USERS solo se usa para la migración inicial.
# Los usuarios en producción se gestionan en la BD (tabla users).

# Supervisor predeterminado en formularios
DEFAULT_SUPERVISOR = 'MB'

# Días sin lectura de batería antes de considerar desactualizada
BATTERY_STALE_DAYS = 90

# Umbral de alerta de batería baja (%)
BATTERY_ALERT_PCT = 25

# Voltajes de referencia (3 baterías AA)
BATTERY_MAX_V = 4.5   # 100% — baterías nuevas
BATTERY_MIN_V = 2.7   # 0%   — baterías agotadas
```

### Cambiar el número de días para alerta de batería desactualizada

En `config.py`, cambia `BATTERY_STALE_DAYS = 90` al número de días deseado. Reinicia el servidor.

### Cambiar puerto del servidor

En `app.py`, modifica la línea:
```python
app.run(host='0.0.0.0', port=5000, debug=False)
```

---

## 14. Resolución de problemas

### "No aparece mi mantenimiento en la lista"

La lista de mantenimiento solo muestra cerraduras de sectores programados para el trimestre seleccionado.

**Solución:**
1. Ve a **Cerraduras** → busca la habitación → clic en el número
2. Pestaña **🔧 Mantenimientos** — el registro estará ahí
3. O usa **Historial** (Sidebar → 📋 Historial)

### "Registré la batería pero no aparece en el módulo de Baterías"

Verifica que al guardar el formulario de mantenimiento sí ingresaste un valor en el campo de voltaje. Si el campo quedó vacío, la batería no se guarda.

Para registrar una batería de un manto ya guardado: ve al detalle de la cerradura → botón "+ Registrar Lectura".

### "No puedo iniciar sesión"

- Verifica usuario y contraseña (son sensibles a mayúsculas)
- Si olvidaste la contraseña, pide al administrador que la cambie en **Admin → Usuarios**
- Si no hay ningún admin disponible, edita directamente la BD o ejecuta `add_users_table.py` después de actualizar `config.py`

### "El servidor no inicia"

1. Verifica que SQL Server esté corriendo
2. Verifica que el ODBC Driver 17 esté instalado
3. Revisa el mensaje de error en la terminal
4. Verifica la configuración en `config.py` (DB_SERVER, DB_NAME)

### "Necesito agregar una cerradura que no existe"

Sidebar → ➕ Nueva Cerradura. Selecciona el sector correspondiente e ingresa el código de habitación.

---

## 15. Glosario

| Término | Significado |
|---------|------------|
| **Q1 / Q2 / Q3 / Q4** | Trimestres del año (Q1=Ene–Mar, Q2=Abr–Jun, Q3=Jul–Sep, Q4=Oct–Dic) |
| **Sector** | Grupo de habitaciones (100, 200, 300, 400, 500+salones) |
| **Manto preventivo** | Revisión planificada por trimestre según calendario del sector |
| **Manto correctivo** | Revisión por falla o incidente específico |
| **Voltaje total** | Suma del voltaje de las 3 baterías AA en serie |
| **Batería baja** | Nivel < 25% (voltaje ≈ < 3.15V) |
| **Batería crítica** | Nivel < 10% (voltaje ≈ < 2.88V) — cambio inmediato |
| **Lectura desactualizada** | Sin medición de batería en más de 90 días |
| **SIS.PHA.REG.026** | Código del documento oficial de registro de mantenimiento |
| **Upsert** | Actualizar si ya existe, insertar si no (comportamiento del formulario al guardar) |

---

*Documento generado: Abril 2026 — Locks Manager PHA Hotel*
