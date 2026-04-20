"""Duplicate detection and classification."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple

from .config import DeteccionDuplicadosConfig
from .metadata import MetadataExtractor
from .file_ops import FileOperations


@dataclass
class FileInfo:
    """Información completa del archivo."""
    ruta: Path
    hash: str
    hash_rapido: str
    fecha: Optional[datetime]
    resolucion: Optional[Tuple[int, int]]
    tamano: int
    categoria: Optional[str] = None
    es_captura: bool = False


class DuplicateDetector:
    """Detecta y clasifica archivos duplicados."""

    def __init__(self, config: DeteccionDuplicadosConfig):
        """
        Inicializa el detector con la configuración.

        Args:
            config: Configuración de detección de duplicados
        """
        self.config = config
        self.extractor = MetadataExtractor(None)
        self.operaciones = FileOperations()
        self.registro_hashes: Dict[str, "FileInfo"] = {}

    def es_duplicado(
        self,
        ruta: Path,
        tamano: int
    ) -> Tuple[bool, Optional[FileInfo], str]:
        """
        Detecta si un archivo es duplicado usando método combinado.

        Args:
            ruta: Ruta al archivo
            tamano: Tamaño del archivo en bytes

        Returns:
            Tuple(es_duplicado: bool, info_original: Optional[FileInfo], tipo: str)
            El tipo puede ser: "", "copia_exacta", "version_inferior", "version_superior", "copia_posterior"
        """
        if not self.config.activado:
            return (False, None, "")

        # 1. Filter by size
        candidatos = [
            info for info in self.registro_hashes.values()
            if info.tamano == tamano
        ]

        if not candidatos:
            return (False, None, "")

        # 2. Fast hash
        hash_rapido = self.operaciones.calcular_hash_rapido(ruta)
        if hash_rapido is None:
            return (False, None, "")

        for candidato in candidatos:
            if hash_rapido == candidato.hash_rapido:
                # 3. Full hash for confirmation
                hash_completo = self.operaciones.calcular_hash_completo(ruta)
                if hash_completo and hash_completo == candidato.hash:
                    # Is duplicate, determine type
                    tipo = self._determinar_tipo_duplicado(ruta, candidato)
                    return (True, candidato, tipo)

        return (False, None, "")

    def _determinar_tipo_duplicado(
        self,
        archivo: Path,
        original: FileInfo
    ) -> str:
        """
        Determina el tipo de duplicado usando criterios inteligentes.

        Args:
            archivo: El archivo siendo procesado
            original: La información del archivo original

        Returns:
            Tipo de duplicado: "copia_exacta", "version_inferior", "version_superior", "copia_posterior"
        """
        fecha_nueva = self.extractor.extraer_fecha_mas_antigua(archivo)
        resolucion_nueva = self.extractor.extraer_resolucion(archivo)

        if not fecha_nueva or not original.fecha:
            return "copia_exacta"

        fecha_candidata = datetime.strptime(fecha_nueva, "%Y-%m-%d %H:%M:%S")
        diferencia_tiempo = abs((fecha_candidata - original.fecha).total_seconds())
        umbral = self.config.umbral_tiempo_version

        # If dates are close (< 1 hour), compare resolution
        if diferencia_tiempo < umbral:
            if resolucion_nueva and original.resolucion:
                pixeles_nuevos = resolucion_nueva[0] * resolucion_nueva[1]
                pixeles_originales = original.resolucion[0] * original.resolucion[1]

                if pixeles_nuevos < pixeles_originales:
                    return "version_inferior"
                elif pixeles_nuevos > pixeles_originales:
                    return "version_superior"
            return "copia_exacta"

        # If dates are far apart, it is a later copy
        if fecha_candidata > original.fecha:
            return "copia_posterior"

        return "copia_exacta"

    def decidir_cual_conservar(
        self,
        archivo: Path,
        original: FileInfo,
        tipo_duplicado: str
    ) -> bool:
        """
        Decide si conservar el archivo nuevo o el original.

        Args:
            archivo: El archivo siendo procesado
            original: La información del archivo original
            tipo_duplicado: El tipo de duplicado detectado

        Returns:
            True si debemos REEMPLAZAR el original con el nuevo
        """
        if tipo_duplicado == "version_superior":
            # El nuevo tiene mejor resolución y fecha cercana
            return True

        if tipo_duplicado == "version_inferior":
            # El original es mejor
            return False

        # Para copias exactas y copias posteriores, conservar el original
        return False

    def registrar_archivo(
        self,
        ruta: Path,
        hash_completo: str,
        fecha: Optional[datetime],
        resolucion: Optional[Tuple[int, int]],
        tamano: int,
        categoria: Optional[str] = None,
        es_captura: bool = False
    ) -> None:
        """
        Registra un archivo en el índice de hashes.

        Args:
            ruta: Ruta al archivo
            hash_completo: Hash SHA256 completo
            fecha: Fecha del archivo
            resolucion: Resolución (ancho, alto)
            tamano: Tamaño en bytes
            categoria: Categoría del archivo (opcional)
            es_captura: Si es una captura de pantalla
        """
        info = FileInfo(
            ruta=ruta,
            hash=hash_completo,
            fecha=fecha,
            resolucion=resolucion,
            tamano=tamano,
            categoria=categoria,
            es_captura=es_captura
        )
        self.registro_hashes[hash_completo] = info


