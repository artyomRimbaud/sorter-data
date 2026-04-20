"""Extracción de metadatos de archivos (EXIF, QuickTime, XMP)."""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config import Configuracion


class MetadataExtractor:
    """Extrae metadatos de archivos multimedia usando exiftool."""

    # Jerarquía de fechas por confiabilidad (de más a menos confiable)
    DATE_HIERARCHY = [
        # Nivel 1: Más confiable (EXIF fotos)
        ["EXIF:DateTimeOriginal", "EXIF:CreateDate", "EXIF:DateTimeDigitized"],
        # Nivel 2: Muy confiable (videos)
        ["QuickTime:CreateDate", "QuickTime:MediaCreateDate", "QuickTime:TrackCreateDate"],
        # Nivel 3: Confiable (otros metadatos)
        ["XMP:CreateDate", "XMP:DateCreated", "IPTC:DateCreated"],
        # Nivel 4: Último recurso (fechas de archivo)
        ["File:FileModifyDate"],
    ]

    def __init__(self, config: Configuracion):
        """
        Inicializa el extractor con la configuración.

        Args:
            config: Instancia de Configuracion
        """
        self.config = config
        self._exiftool_verified = False

    def verificar_exiftool(self) -> bool:
        """
        Verifica si exiftool está instalado y disponible.

        Returns:
            True si exiftool está disponible
        """
        if self._exiftool_verified:
            return True

        try:
            resultado = subprocess.run(
                ['exiftool', '-ver'],
                capture_output=True,
                check=True,
                timeout=5
            )
            self._exiftool_verified = True
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def extraer_fechas_todas(self, ruta: Path) -> Dict[str, str]:
        """
        Extrae todas las fechas de metadatos de un archivo.

        Args:
            ruta: Ruta al archivo

        Returns:
            Diccionario {etiqueta: valor_string} con todas las fechas
        """
        if not self.verificar_exiftool():
            raise RuntimeError("ExifTool no está instalado")

        try:
            cmd = ['exiftool', '-json', '-G', '-time:all', str(ruta)]
            resultado = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if resultado.returncode != 0:
                return {}

            metadatos = json.loads(resultado.stdout)[0]
            fechas = {}

            for etiqueta, valor in metadatos.items():
                # Ignorar GPS para fechas
                if 'GPS' in etiqueta and 'Date' in etiqueta:
                    continue
                # Solo guardar etiquetas de fecha
                if 'Date' in etiqueta or 'Time' in etiqueta:
                    fechas[etiqueta] = valor

            return fechas
        except (json.JSONDecodeError, subprocess.TimeoutExpired, IndexError):
            return {}
        except Exception as e:
            return {}

    def extraer_fecha_mas_antigua(self, ruta: Path) -> Optional[str]:
        """
        Extracts the oldest date from metadata.

        Args:
            path: Path to the file

        Returns:
            The oldest date as a string or None if no dates exist
        """
        todas_fechas = self.extraer_fechas_todas(ruta)

        if not todas_fechas:
            return None

        # Parse dates and find the oldest
        fechas_parseadas: List[Tuple[str, datetime]] = []

        for etiqueta, valor in todas_fechas.items():
            fecha = self._parsear_fecha_string(valor)
            if fecha:
                fechas_parseadas.append((etiqueta, fecha))

        if not fechas_parseadas:
            return None

        # Return the oldest
        fecha_min = min(fechas_parseadas, key=lambda x: x[1])
        return fecha_min[1].strftime('%Y-%m-%d %H:%M:%S')

    def extraer_resolucion(self, ruta: Path) -> Optional[Tuple[int, int]]:
        """
        Extracts the resolution of an image or video.

        Args:
            path: Path to the file

        Returns:
            Tuple(width, height) or None if it cannot be determined
        """
        if not self.verificar_exiftool():
            raise RuntimeError("ExifTool is not installed")

        try:
            cmd = ['exiftool', '-json', '-ImageWidth', '-ImageHeight', str(ruta)]
            resultado = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )

            if resultado.returncode != 0:
                return None

            metadatos = json.loads(resultado.stdout)[0]

            ancho = None
            alto = None

            for key, value in metadatos.items():
                if 'width' in key.lower() and isinstance(value, (int, float)):
                    ancho = int(value)
                if 'height' in key.lower() and isinstance(value, (int, float)):
                    alto = int(value)

            if ancho and alto:
                return (ancho, alto)
            return None
        except Exception:
            return None

    def extraer_fechas_organizadas(
        self,
        ruta: Path,
        ignorar_file: bool = True
    ) -> List[Dict[str, str]]:
        """
        Extracts dates organized by hierarchy level.

        Args:
            ruta: Path to the file
            ignorar_file: If True, ignores File: labels in hierarchy

        Returns:
            List of dictionaries, one per level, with {label: date_string}
        """
        todas_fechas = self.extraer_fechas_todas(ruta)

        if not todas_fechas:
            return []

        # Create structure for the levels
        fechas_por_nivel: List[Dict[str, str]] = [
            {} for _ in range(len(self.DATE_HIERARCHY))
        ]

        for etiqueta, valor in todas_fechas.items():
            # Ignore File: if configured
            if ignorar_file and etiqueta.startswith('File:'):
                continue

            for nivel, etiquetas_nivel in enumerate(self.DATE_HIERARCHY):
                if any(etiq in etiqueta for etiq in etiquetas_nivel):
                    fechas_por_nivel[nivel][etiqueta] = valor
                    break

        return fechas_por_nivel

    def _parsear_fecha_string(self, fecha_str: str) -> Optional[datetime]:
        """
        Parse a date from exiftool format to standard format.

        Args:
            fecha_str: The date as a string from exiftool

        Returns:
            datetime or None
        """
        if not isinstance(fecha_str, str):
            return None

        # Clean the string (remove timezones and other suffixes)
        fecha_limpia = fecha_str.split('+')[0].strip()

        formatos = [
            '%Y:%m:%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%Y:%m:%d',
            '%Y-%m-%d',
        ]

        for formato in formatos:
            try:
                return datetime.strptime(fecha_limpia, formato)
            except ValueError:
                continue

        return None
