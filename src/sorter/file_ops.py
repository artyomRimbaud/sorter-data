"""Operaciones de archivos: mover, copiar, verificación de integridad."""

import hashlib
import shutil
from pathlib import Path
from typing import Optional, Tuple


class FileOperations:
    """Maneja operaciones de archivos con verificación de integridad."""

    CHUNK_SIZE = 8192  # Tamaño de bloque para hash

    @staticmethod
    def calcular_hash_completo(ruta: Path) -> Optional[str]:
        """
        Calcula el hash SHA256 completo de un archivo.

        Args:
            ruta: Ruta al archivo

        Returns:
            Hash hexadecimal o None si hay un error
        """
        try:
            hash_obj = hashlib.sha256()
            with open(ruta, "rb") as f:
                while chunk := f.read(FileOperations.CHUNK_SIZE):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except (OSError, IOError) as e:
            return None

    @staticmethod
    def calcular_hash_rapido(ruta: Path, bytes_leer: int = 65536) -> Optional[str]:
        """
        Calcula un hash rápido usando los primeros bytes del archivo.

        Args:
            ruta: Ruta al archivo
            bytes_leer: Número de bytes para el hash (por defecto 64KB)

        Returns:
            Hash hexadecimal o None si hay un error
        """
        try:
            hash_obj = hashlib.sha256()
            with open(ruta, "rb") as f:
                hash_obj.update(f.read(bytes_leer))
            return hash_obj.hexdigest()
        except (OSError, IOError) as e:
            return None

    @staticmethod
    def crear_directorio(ruta: Path, parents: bool = True) -> bool:
        """
        Crea un directorio y sus directorios padres si es necesario.

        Args:
            ruta: Ruta al directorio a crear
            parents: Si True, crea directorios padres

        Returns:
            True si se creó o ya existe, False si hay un error
        """
        try:
            ruta.mkdir(parents=parents, exist_ok=True)
            return True
        except OSError as e:
            return False

    def mover_archivo(
        self,
        origen: Path,
        destino: Path,
        verificar_integridad: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Mueve un archivo desde el origen al destino con verificación.

        Args:
            origen: Ruta al archivo de origen
            destino: Ruta al destino
            verificar_integridad: Si True, verifica hash después de mover

        Returns:
            Tuple[exito: bool, error: Optional[str]]
        """
        # Verificar que el origen existe
        if not origen.exists():
            return False, f"El archivo de origen no existe: {origen}"

        # Calcular hash antes si la verificación está habilitada
        hash_antes: Optional[str] = None
        if verificar_integridad:
            hash_antes = self.calcular_hash_completo(origen)
            if hash_antes is None:
                return False, f"No se pudo calcular el hash para: {origen}"

        # Crear directorio de destino
        if not self.crear_directorio(destino.parent):
            return False, f"No se pudo crear el directorio: {destino.parent}"

        try:
            # Mover el archivo
            shutil.move(str(origen), str(destino))
        except (shutil.Error, OSError) as e:
            return False, f"Error moviendo {origen.name}: {e}"

        # Verificar integridad si está habilitada
        if verificar_integridad and hash_antes is not None:
            hash_despues = self.calcular_hash_completo(destino)
            if hash_despues is None or hash_antes != hash_despues:
                # Intentar recuperar si la verificación falla
                if destino.exists():
                    try:
                        destino.unlink()
                    except OSError:
                        pass
                return False, "El hash después de mover no coincide"

        return True, None

    def copiar_archivo(
        self,
        origen: Path,
        destino: Path,
        verificar_integridad: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Copia un archivo desde el origen al destino con verificación.

        Args:
            origen: Ruta al archivo de origen
            destino: Ruta al destino
            verificar_integridad: Si True, verifica hash después de copiar

        Returns:
            Tuple[exito: bool, error: Optional[str]]
        """
        # Verificar que el origen existe
        if not origen.exists():
            return False, f"El archivo de origen no existe: {origen}"

        # Calcular hash antes si la verificación está habilitada
        hash_antes: Optional[str] = None
        if verificar_integridad:
            hash_antes = self.calcular_hash_completo(origen)
            if hash_antes is None:
                return False, f"No se pudo calcular el hash para: {origen}"

        # Crear directorio de destino
        if not self.crear_directorio(destino.parent):
            return False, f"No se pudo crear el directorio: {destino.parent}"

        try:
            # Copiar el archivo preservando metadatos
            shutil.copy2(str(origen), str(destino))
        except (shutil.Error, OSError) as e:
            return False, f"Error copiando {origen.name}: {e}"

        # Verificar integridad si está habilitada
        if verificar_integridad and hash_antes is not None:
            hash_despues = self.calcular_hash_completo(destino)
            if hash_despues is None or hash_antes != hash_despues:
                return False, "El hash después de copiar no coincide"

        return True, None

    def simular_mover(
        self,
        origen: Path,
        destino: Path
    ) -> Tuple[bool, str]:
        """
        Simula mover un archivo sin realizar operaciones reales.

        Args:
            origen: Ruta al archivo de origen
            destino: Ruta al destino

        Returns:
            Tuple[exito: bool, mensaje: str]
        """
        if not origen.exists():
            return False, f"El archivo de origen no existe: {origen}"
        return True, f"[SIMULACIÓN] movería {origen} -> {destino}"

    def simular_copiar(
        self,
        origen: Path,
        destino: Path
    ) -> Tuple[bool, str]:
        """
        Simula copiar un archivo sin realizar operaciones reales.

        Args:
            origen: Ruta al archivo de origen
            destino: Ruta al destino

        Returns:
            Tuple[exito: bool, mensaje: str]
        """
        if not origen.exists():
            return False, f"El archivo de origen no existe: {origen}"
        return True, f"[SIMULACIÓN] copiaría {origen} -> {destino}"


