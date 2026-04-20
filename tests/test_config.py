"""Tests for the configuration module."""

import pytest
from pathlib import Path
import tempfile
import json

from sorter.config import Configuracion, Preset, create_default_config
from sorter.preset_manager import PresetValidationError


class TestPresetDataclass:
    """Tests for the Preset dataclass."""

    def test_valid_preset_basic(self):
        """Test a valid preset with minimum required fields."""
        preset = Preset(
            nombre="test-preset",
            modo="mover",
            inicio=["/source"],
            fin="/destination"
        )
        assert preset.nombre == "test-preset"
        assert preset.modo == "mover"
        assert preset.inicio == ["/source"]
        assert preset.fin == "/destination"
        assert preset.activo is True
        assert preset.descripcion is None

    def test_valid_preset_copy_mode(self):
        """Test a valid preset with copy mode."""
        preset = Preset(
            nombre="copy-preset",
            modo="copiar",
            fin="/destination"
        )
        assert preset.modo == "copiar"

    def test_preset_to_dict(self):
        """Test Preset.to_dict() serialization."""
        preset = Preset(
            nombre="test",
            modo="mover",
            inicio=["/src"],
            fin="/dst",
            activo=False,
            descripcion="Test preset"
        )
        result = preset.to_dict()
        assert result["nombre"] == "test"
        assert result["modo"] == "mover"
        assert result["inicio"] == ["/src"]
        assert result["fin"] == "/dst"
        assert result["activo"] is False
        assert result["descripcion"] == "Test preset"

    def test_preset_from_dict(self):
        """Test Preset.from_dict() deserialization."""
        data = {
            "nombre": "test-preset",
            "modo": "mover",
            "inicio": ["/source"],
            "fin": "/destination",
            "activo": False,
            "descripcion": "Test preset"
        }
        preset = Preset.from_dict(data)
        assert preset.nombre == "test-preset"
        assert preset.modo == "mover"
        assert preset.activo is False

    def test_preset_from_dict_without_description(self):
        """Test Preset.from_dict() without optional fields."""
        data = {
            "nombre": "test",
            "modo": "copiar",
            "fin": "/dst"
        }
        preset = Preset.from_dict(data)
        assert preset.nombre == "test"
        assert preset.modo == "copiar"
        assert preset.activo is True
        assert preset.inicio is None
        assert preset.descripcion is None


class TestPresetValidation:
    """Tests for Preset validation."""

    def test_invalid_preset_without_name(self):
        """Test that preset without name raises error."""
        data = {"modo": "mover", "fin": "/dst"}
        with pytest.raises(ValueError, match="nombre"):
            Preset.from_dict(data)

    def test_invalid_preset_without_modo(self):
        """Test that preset without mode raises error."""
        data = {"nombre": "test", "fin": "/dst"}
        with pytest.raises(ValueError):
            Preset.from_dict(data)

    def test_invalid_preset_invalid_modo(self):
        """Test that preset with invalid mode raises error."""
        data = {"nombre": "test", "modo": "invalid", "fin": "/dst"}
        with pytest.raises(ValueError, match="mover"):
            Preset.from_dict(data)

    def test_invalid_preset_without_start_or_end(self):
        """Test that preset without start or end raises error."""
        data = {"nombre": "test", "modo": "mover"}
        with pytest.raises(ValueError, match="inicio"):
            Preset.from_dict(data)

    def test_preset_without_start(self):
        """Test preset with only end (no start)."""
        data = {"nombre": "test", "modo": "mover", "fin": "/dst"}
        preset = Preset.from_dict(data)
        assert preset.inicio is None
        assert preset.fin == "/dst"

    def test_preset_without_end(self):
        """Test preset with only start (no end)."""
        data = {"nombre": "test", "modo": "mover", "inicio": ["/src"]}
        preset = Preset.from_dict(data)
        assert preset.inicio == ["/src"]
        assert preset.fin is None


class TestPresetNameValidation:
    """Tests for preset name validation."""

    def test_valid_name_letters_numbers(self):
        """Test preset name with letters and numbers."""
        preset = Preset(
            nombre="test123",
            modo="mover",
            fin="/dst"
        )
        assert preset.nombre == "test123"

    def test_valid_name_with_hyphen(self):
        """Test preset name with hyphen."""
        preset = Preset(
            nombre="my-preset",
            modo="mover",
            fin="/dst"
        )
        assert preset.nombre == "my-preset"

    def test_valid_name_with_underscore(self):
        """Test preset name with underscore."""
        preset = Preset(
            nombre="my_preset",
            modo="mover",
            fin="/dst"
        )
        assert preset.nombre == "my_preset"

    def test_invalid_name_with_spaces(self):
        """Test preset name with spaces is invalid."""
        from sorter.preset_manager import PresetManager, PresetValidationError
        manager = PresetManager()
        with pytest.raises(PresetValidationError, match="letters"):
            manager.create("my preset", "mover", fin="/dst")

    def test_invalid_name_with_special_chars(self):
        """Test preset name with special characters is invalid."""
        from sorter.preset_manager import PresetManager, PresetValidationError
        manager = PresetManager()
        with pytest.raises(PresetValidationError, match="letters"):
            manager.create("my@preset!", "mover", fin="/dst")


class TestConfig:
    """Tests for the Configuracion class."""

    def test_default_config_creation(self):
        """Test create_default_config() function."""
        config = create_default_config()
        assert "operacion" in config
        assert "estructura" in config
        assert "duplicados" in config
        assert "validacion_fechas" in config
        assert "deteccion_capturas" in config
        assert "categorias" in config
        assert "categorias_multimedia" in config
        assert "reportes" in config
        assert "logs" in config

    def test_config_from_dict(self):
        """Test Configuracion.from_dict() with minimal data."""
        data = {
            "operacion": {},
            "estructura": {},
            "duplicados": {},
            "validacion_fechas": {},
            "deteccion_capturas": {},
            "categorias": {},
            "categorias_multimedia": [],
            "reportes": {},
            "logs": {}
        }
        config = Configuracion.from_dict(data)
        assert config.origen == []  # origen is now a list
        assert config.destino_base == ""

    def test_config_loads_origen_destino(self):
        """Test that config loads origen and destino_base fields."""
        data = {
            "operacion": {},
            "estructura": {},
            "duplicados": {},
            "validacion_fechas": {},
            "deteccion_capturas": {},
            "categorias": {},
            "categorias_multimedia": [],
            "reportes": {},
            "logs": {},
            "origen": "/source",
            "destino_base": "/destination"
        }
        config = Configuracion.from_dict(data)
        assert config.origen == ["/source"]  # origen is now a list
        assert config.destino_base == "/destination"

    def test_config_origen_string_normalization(self):
        """Test that string origen is normalized to list."""
        data = {
            "operacion": {},
            "estructura": {},
            "duplicados": {},
            "validacion_fechas": {},
            "deteccion_capturas": {},
            "categorias": {},
            "categorias_multimedia": [],
            "reportes": {},
            "logs": {},
            "origen": "/source/path",
            "destino_base": "/destination"
        }
        config = Configuracion.from_dict(data)
        # String should be normalized to list
        assert isinstance(config.origen, list)
        assert config.origen == ["/source/path"]

    def test_config_origen_list_preserved(self):
        """Test that list origen is preserved."""
        data = {
            "operacion": {},
            "estructura": {},
            "duplicados": {},
            "validacion_fechas": {},
            "deteccion_capturas": {},
            "categorias": {},
            "categorias_multimedia": [],
            "reportes": {},
            "logs": {},
            "origen": ["/src1", "/src2", "/src3"],
            "destino_base": "/destination"
        }
        config = Configuracion.from_dict(data)
        assert isinstance(config.origen, list)
        assert config.origen == ["/src1", "/src2", "/src3"]

    def test_config_origen_empty_default(self):
        """Test that empty/None origen defaults to empty list."""
        data = {
            "operacion": {},
            "estructura": {},
            "duplicados": {},
            "validacion_fechas": {},
            "deteccion_capturas": {},
            "categorias": {},
            "categorias_multimedia": [],
            "reportes": {},
            "logs": {},
            "destino_base": "/destination"
        }
        config = Configuracion.from_dict(data)
        assert config.origen == []
