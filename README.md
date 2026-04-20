
# sorter-data

Organizador de archivos multimedia y documentos basado en metadatos, con detección inteligente de duplicados.

## ¿Qué hace?

Analiza los metadatos EXIF, QuickTime y XMP de tus archivos para organizarlos automáticamente en una estructura de carpetas por categoría y fecha. Detecta duplicados comparando contenido, resolución y fecha, y genera reportes detallados del proceso.

## Características

- Organización por metadatos reales (EXIF, QuickTime, XMP) con validación cruzada de fechas
- Detección de duplicados por hash combinado + resolución + fecha
- Tres modos de operación: mover, copiar o simulación (no destructivo)
- Verificación de integridad SHA256 antes y después de cada operación
- Sistema de presets para reutilizar configuraciones frecuentes
- Reportes en TXT, CSV y log de errores

## Requisitos

- Python >= 3.10
- [ExifTool](https://exiftool.org/) instalado en el sistema

## Instalación

```bash
# Ubuntu/Debian
sudo apt-get install libimage-exiftool-perl

# macOS
brew install exiftool
```

```bash
git clone https://github.com/artyomRimbaud/sorter-data.git
cd sorter-data
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

## Uso básico

```bash
# Simular organización (recomendado antes de ejecutar)
sorter run move --start ~/fotos --end ~/almacenamiento --simulation

# Mover archivos
sorter run move --start ~/fotos --end ~/almacenamiento

# Copiar archivos (preserva el origen)
sorter run copy --start ~/fotos --end ~/almacenamiento
```

## Estructura de salida

```
destino/
├── multimedia/
│   ├── fotos/2024/04-Abril/
│   ├── videos/2024/04-Abril/
│   └── audios/2024/04-Abril/
├── documentos/
├── otros/
└── .sorter-data_reports/2024-04-06_15-30-45/
    ├── report.txt
    ├── duplicates.csv
    └── errors.log
```

Para referencia completa de comandos, configuración y resolución de problemas, consulta [USO.md](./USO.md).

## Licencia

MIT License — Copyright (c) 2026 artyomRimbaud