"""Preset management: create, read, list, delete presets."""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from .config import Preset, get_default_preset_path


class PresetManagerError(Exception):
    """Base exception for preset manager errors."""
    pass


class PresetValidationError(PresetManagerError):
    """Exception raised when preset validation fails."""
    pass


class PresetNotFoundError(PresetManagerError):
    """Exception raised when a preset is not found."""
    pass


class PresetManager:
    """Manages preset operations (create, read, list, delete)."""

    def __init__(self, presets_dir: Optional[Path] = None):
        """
        Initialize the preset manager.

        Args:
            presets_dir: Directory to store presets. Defaults to ~/.config/sorter/presets/
        """
        self.presets_dir = presets_dir or get_default_preset_path()

    def _ensure_presets_dir(self) -> None:
        """Create the presets directory if it doesn't exist."""
        self.presets_dir.mkdir(parents=True, exist_ok=True)

    def _validate_preset_name(self, nombre: str) -> bool:
        """
        Validate that a preset name is filesystem-safe.

        Args:
            nombre: The preset name to validate

        Returns:
            True if valid, raises PresetValidationError otherwise
        """
        # Check for empty name
        if not nombre:
            raise PresetValidationError("Preset name cannot be empty")

        # Check length
        if len(nombre) > 64:
            raise PresetValidationError("Preset name too long (max 64 characters)")

        # Check for valid characters: letters, numbers, hyphens, underscores
        # No spaces or special characters
        if not re.match(r'^[a-zA-Z0-9_-]+$', nombre):
            raise PresetValidationError(
                "Preset name must contain only letters, numbers, hyphens, and underscores"
            )

        return True

    def _get_preset_path(self, nombre: str) -> Path:
        """Get the full path to a preset file."""
        return self.presets_dir / f"{nombre}.json"

    def create(self, nombre: str, modo: str, inicio: Optional[List[str]] = None,
               fin: Optional[str] = None, activo: bool = True,
               descripcion: Optional[str] = None) -> Preset:
        """
        Create a new preset.

        Args:
            nombre: Name of the preset (filesystem-safe)
            modo: Operation mode ('mover' or 'copiar')
            inicio: Source path(s) as a list
            fin: Destination path
            activo: Whether the preset is active
            descripcion: Optional description

        Returns:
            The created Preset object

        Raises:
            PresetValidationError: If validation fails
            PresetManagerError: If preset already exists
        """
        self._validate_preset_name(nombre)

        # Check if preset already exists
        preset_path = self._get_preset_path(nombre)
        if preset_path.exists():
            raise PresetManagerError(f"Preset '{nombre}' already exists")

        # Validate required fields
        if not inicio and not fin:
            raise PresetValidationError("Preset must have either 'inicio' (start) or 'fin' (end)")

        # Create preset
        preset = Preset(
            nombre=nombre,
            modo=modo,
            inicio=inicio,
            fin=fin,
            activo=activo,
            descripcion=descripcion
        )

        # Ensure directory exists and save
        self._ensure_presets_dir()
        with open(preset_path, 'w', encoding='utf-8') as f:
            json.dump(preset.to_dict(), f, indent=2, ensure_ascii=False)

        return preset

    def read(self, nombre: str) -> Preset:
        """
        Read a preset by name.

        Args:
            nombre: Name of the preset to read

        Returns:
            The Preset object

        Raises:
            PresetNotFoundError: If preset doesn't exist
            PresetValidationError: If preset data is invalid
        """
        preset_path = self._get_preset_path(nombre)

        if not preset_path.exists():
            raise PresetNotFoundError(f"Preset '{nombre}' not found")

        try:
            with open(preset_path, 'r', encoding='utf-8') as f:
                datos = json.load(f)

            return Preset.from_dict(datos)
        except json.JSONDecodeError as e:
            raise PresetValidationError(f"Invalid preset file format: {e}")
        except ValueError as e:
            raise PresetValidationError(f"Invalid preset data: {e}")

    def list(self) -> List[Preset]:
        """
        List all available presets.

        Returns:
            List of Preset objects
        """
        self._ensure_presets_dir()

        presets = []
        for preset_file in self.presets_dir.glob("*.json"):
            try:
                with open(preset_file, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                presets.append(Preset.from_dict(datos))
            except (json.JSONDecodeError, ValueError):
                # Skip invalid preset files
                continue

        return presets

    def delete(self, nombre: str) -> bool:
        """
        Delete a preset by name.

        Args:
            nombre: Name of the preset to delete

        Returns:
            True if deleted, False if not found

        Raises:
            PresetNotFoundError: If preset doesn't exist (optional, could just return False)
        """
        preset_path = self._get_preset_path(nombre)

        if not preset_path.exists():
            raise PresetNotFoundError(f"Preset '{nombre}' not found")

        preset_path.unlink()
        return True

    def exists(self, nombre: str) -> bool:
        """
        Check if a preset exists.

        Args:
            nombre: Name of the preset to check

        Returns:
            True if the preset exists, False otherwise
        """
        return self._get_preset_path(nombre).exists()

    def update(self, nombre: str, **kwargs) -> Preset:
        """
        Update an existing preset.

        Args:
            nombre: Name of the preset to update
            **kwargs: Fields to update (modo, inicio, fin, activo, descripcion)

        Returns:
            The updated Preset object

        Raises:
            PresetNotFoundError: If preset doesn't exist
            PresetValidationError: If validation fails
        """
        if not self.exists(nombre):
            raise PresetNotFoundError(f"Preset '{nombre}' not found")

        # Read existing preset
        preset = self.read(nombre)

        # Update fields
        if 'modo' in kwargs:
            if kwargs['modo'] not in ('mover', 'copiar'):
                raise PresetValidationError("Mode must be 'mover' or 'copiar'")
            preset.modo = kwargs['modo']

        if 'inicio' in kwargs:
            preset.inicio = kwargs['inicio']

        if 'fin' in kwargs:
            preset.fin = kwargs['fin']

        if 'activo' in kwargs:
            preset.activo = kwargs['activo']

        if 'descripcion' in kwargs:
            preset.descripcion = kwargs['descripcion']

        # Save updated preset
        self._ensure_presets_dir()
        preset_path = self._get_preset_path(nombre)
        with open(preset_path, 'w', encoding='utf-8') as f:
            json.dump(preset.to_dict(), f, indent=2, ensure_ascii=False)

        return preset


def create_preset(
    nombre: str,
    modo: str,
    inicio: Optional[List[str]] = None,
    fin: Optional[str] = None,
    presets_dir: Optional[Path] = None
) -> Preset:
    """
    Create a preset using the manager's default directory.

    Args:
        nombre: Name of the preset
        modo: Operation mode ('mover' or 'copiar')
        inicio: Source path(s)
        fin: Destination path
        presets_dir: Custom presets directory

    Returns:
        The created Preset object
    """
    manager = PresetManager(presets_dir)
    return manager.create(nombre, modo, inicio, fin)


def get_preset_manager(presets_dir: Optional[Path] = None) -> PresetManager:
    """
    Get a preset manager instance with the default directory.

    Args:
        presets_dir: Custom presets directory

    Returns:
        PresetManager instance
    """
    return PresetManager(presets_dir)
