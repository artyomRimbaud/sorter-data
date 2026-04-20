# Referencia técnica — sorter-data

## Comandos CLI

### `sorter run`

Organiza archivos desde uno o varios orígenes hacia un destino.

```bash
sorter run <modo> --start <ruta> --end <ruta> [--simulation]
```

| Argumento | Descripción |
|-----------|-------------|
| `modo` | `move` (por defecto) o `copy` |
| `--start, -s` | Ruta(s) de origen. Separar con comas para múltiples rutas |
| `--end, -e` | Ruta de destino |
| `--simulation` | Analiza y genera reportes sin mover ni copiar archivos |

```bash
# Múltiples orígenes
sorter run move --start ~/descargas,/tmp/fotos --end ~/almacenamiento
```

---

### `sorter preset`

Guarda y reutiliza configuraciones frecuentes. Los presets se almacenan como JSON en `~/.config/sorter-data/presets/`.

```bash
# Crear
sorter preset --create <nombre> --run <modo> --start <ruta> --end <ruta>

# Ejecutar
sorter preset <nombre>

# Ejecutar en simulación
sorter preset <nombre> simulation

# Listar
sorter preset list

# Eliminar
sorter preset <nombre> delete
```

Los nombres de preset solo admiten letras, números, guiones y guiones bajos.

**Ejemplo de archivo de preset:**
```json
{
  "nombre": "personal",
  "modo": "mover",
  "inicio": ["/home/usuario/descargas"],
  "fin": "/home/usuario/almacenamiento",
  "activo": true
}
```

---

### `sorter info`

Analiza un directorio y muestra información de archivos sin modificar nada. El reporte se guarda en el origen.

```bash
sorter info --start <ruta>
```

---

## Configuración avanzada

No se requiere archivo de configuración para el uso estándar. Si necesitas personalizar comportamientos específicos, crea un `config.json` en el directorio raíz del proyecto.

### `operacion`

| Opción | Por defecto | Descripción |
|--------|-------------|-------------|
| `recursivo` | `true` | Procesar subdirectorios recursivamente |
| `modo_prueba` | `false` | Equivalente a `--simulation` |
| `modo_operacion` | `mover` | `mover` o `copiar` |
| `verificar_integridad` | `true` | Verificación SHA256 tras mover/copiar |
| `ignorar_grupo_file` | `true` | Ignorar archivos que empiezan con `group` |

### `estructura`

| Opción | Por defecto | Descripción |
|--------|-------------|-------------|
| `multimedia_base` | `multimedia` | Carpeta base para multimedia |
| `documentos_base` | `documentos` | Carpeta base para documentos |
| `otros_base` | `otros` | Carpeta base para otros |
| `carpeta_duplicados` | `duplicados` | Subcarpeta para duplicados |
| `carpeta_sospechosas` | `fechas_sospechosas` | Subcarpeta para fechas inconsistentes |
| `carpeta_sin_fecha` | `sin_fecha` | Subcarpeta para archivos sin fecha |
| `formato_fecha` | `{year}/{month:02d}-{month_name}` | Plantilla de ruta por fecha |

### `duplicados`

| Opción | Por defecto | Descripción |
|--------|-------------|-------------|
| `activado` | `true` | Activar detección de duplicados |
| `metodo` | `combinado` | `rapido` (solo hash) o `combinado` (hash + resolución + fecha) |
| `criterio_conservar` | `inteligente` | `inteligente` o `mas_reciente` |
| `umbral_tiempo_version` | `3600` | Segundos de tolerancia para considerar versiones |

### `validacion_fechas`

| Opción | Por defecto | Descripción |
|--------|-------------|-------------|
| `activado` | `true` | Activar validación de fechas |
| `solo_multimedia` | `true` | Aplicar solo a archivos multimedia |
| `fecha_minima_absoluta` | `1990-01-01` | Fecha más temprana aceptada |
| `fecha_maxima_relativa_anos` | `1` | Años hacia el futuro permitidos |
| `requiere_validacion_cruzada` | `true` | Exigir coincidencia entre fuentes de metadatos |
| `tolerancia_validacion_dias` | `1` | Días de margen en validación cruzada |
| `minimo_fechas_coincidentes` | `1` | Mínimo de fuentes que deben coincidir |
| `fecha_minima_esperada` | `2018-01-01` | Umbral para activar validación cruzada adicional |
| `accion_fecha_antes_esperada` | `validar_cruzada` | Acción para fechas anteriores al umbral |

### `deteccion_capturas`

| Opción | Por defecto | Descripción |
|--------|-------------|-------------|
| `activado` | `true` | Activar detección de capturas de pantalla |
| `como_subdirectorio` | `true` | Mover capturas a subcarpeta `capturas/` |
| `palabras_clave` | `[...]` | Palabras clave para detección por nombre |

### `categorias`

```json
{
  "Fotos":       ["jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff", "heic"],
  "Videos":      ["mp4", "mkv", "mov", "avi", "wmv", "flv", "webm"],
  "Audios":      ["mp3", "flac", "wav", "ogg", "m4a", "aac"],
  "Documentos":  ["pdf", "docx", "doc", "xlsx", "xls", "pptx", "txt", "odt"]
}
```

---

## Tipos de duplicados

| Tipo | Sufijo | Criterio | Acción |
|------|--------|----------|--------|
| Copia exacta | `_copia_exacta` | Mismo hash y fecha | Se mueve a `duplicados/` |
| Versión inferior | `_version_inferior` | Mismo contenido, menor resolución | Se conserva el original |
| Versión superior | `_version_superior` | Mismo contenido, mayor resolución | Reemplaza al original |
| Copia posterior | `_copia_posterior` | Mismo contenido, fecha más reciente | Se conserva el más reciente |

---

## Reportes

Los reportes se generan automáticamente en cada ejecución.

| Ubicación | Modo |
|-----------|------|
| `<destino>/.sorter-data_reports/<timestamp>/` | `run` |
| `<origen>/.sorter-data_reports/<timestamp>/` | `info` |

El timestamp sigue el formato `YYYY-MM-DD_HH-MM-SS`.

### `report.txt`

Resumen estadístico del proceso: archivos procesados, movidos, duplicados encontrados por tipo, archivos sin fecha, fechas sospechosas, capturas detectadas y errores, desglosados por categoría.

### `duplicates.csv`

Registro de cada duplicado detectado con las siguientes columnas:

`Tipo` · `Categoria` · `Archivo_Conservado` · `Archivo_Duplicado` · `Razon` · `Fecha_Conservado` · `Fecha_Duplicado`

### `errors.log`

Log de errores con timestamp, ruta del archivo afectado y descripción del error.

---

## Flujo de trabajo recomendado

```bash
# 1. Analizar el origen
sorter info --start ~/origen

# 2. Simular la operación y revisar reportes
sorter run move --start ~/origen --end ~/destino --simulation

# 3. Ejecutar
sorter run move --start ~/origen --end ~/destino

# 4. Verificar resultados
cat ~/destino/.sorter-data_reports/*/report.txt
```

Si el volumen de archivos es grande o el origen es irrecuperable, se recomienda hacer un respaldo antes del paso 3.

---

## Resolución de problemas

**ExifTool no encontrado**
```
RuntimeError: ExifTool no esta instalado
```
Instalar según el sistema operativo (ver [README](./README.md)) y verificar con `exiftool -ver`.

---

**Permiso denegado**
```
Error moviendo archivo.jpg: Permission denied
```
Verificar permisos con `ls -la` sobre origen y destino. Corregir con `chmod -R u+w <ruta>` si corresponde.

---

**Directorio no encontrado**
```
ERROR: Directory does not exist
```
Crear las rutas con `mkdir -p <ruta>` antes de ejecutar.

---

**Archivos en `sin_fecha/`**
Indica que el archivo no tiene metadatos de fecha legibles. Causas comunes: descargas web, capturas de pantalla, archivos corruptos o formatos sin soporte de metadatos. Revisar manualmente esa carpeta tras cada ejecución.

---

**Preset no encontrado**
```
ERROR: Preset 'nombre' not found
```
Listar presets existentes con `sorter preset list` y recrear si es necesario.