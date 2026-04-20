"""Tests for the date validation module."""

import pytest
from datetime import datetime, timedelta
from pathlib import Path

from sorter.validator import DateValidator, is_suspicious_date
from sorter.config import ValidacionFechasConfig


@pytest.fixture
def config_validacion():
    """Fixture for validation configuration."""
    return ValidacionFechasConfig(
        activado=True,
        solo_multimedia=True,
        fecha_minima_absoluta="1990-01-01",
        fecha_maxima_relativa_anos=1,
        fechas_genericas=["1970-01-01", "1980-01-01", "2000-01-01", "2001-01-01"],
        requiere_validacion_cruzada=True,
        tolerancia_validacion_dias=1,
        minimo_fechas_coincidentes=1,
        fecha_minima_esperada="2018-01-01",
        accion_fecha_antes_esperada="validar_cruzada"
    )


class TestDateValidator:
    """Tests for DateValidator."""

    def test_no_dates(self, config_validacion):
        """Test with empty date dictionary."""
        validador = DateValidator(config_validacion)
        fecha, razon = validador.validar_fecha_inteligente({})
        assert fecha is None
        assert razon == "no_date"

    def test_valid_date_with_cross_validation(self, config_validacion):
        """Test with valid date that requires cross-validation."""
        validador = DateValidator(config_validacion)

        # Dates at different levels (simulate consistency)
        fechas = {
            "EXIF:DateTimeOriginal": datetime(2023, 5, 15, 10, 30, 0),
            "QuickTime:CreateDate": datetime(2023, 5, 15, 10, 30, 30),  # Within tolerance
        }

        fecha, razon = validador.validar_fecha_inteligente(fechas)
        assert razon == "valid"
        assert fecha is not None

    def test_suspicious_generic_date(self, config_validacion):
        """Test with generic date."""
        validador = DateValidator(config_validacion)

        # Generic date 1970-01-01
        fechas = {
            "File:FileModifyDate": datetime(1970, 1, 1, 0, 0, 0),
        }

        fecha, razon = validador.validar_fecha_inteligente(fechas)
        # Should discard generic and find another or mark as suspicious
        assert razon in ["suspicious", "no_date"]

    def test_suspicious_date_function(self, config_validacion):
        """Test for the is_suspicious_date function."""
        fecha_generica = datetime(1970, 1, 1)
        fecha_normal = datetime.now()

        assert is_suspicious_date(fecha_generica, config_validacion) is True
        assert is_suspicious_date(fecha_normal, config_validacion) is False


class TestDateConsistency:
    """Tests for date consistency validation."""

    def test_consistent_validation_success(self, config_validacion):
        """Test that validates dates from different levels match."""
        validador = DateValidator(config_validacion)

        # Consistent dates (same date at different levels)
        fechas_todas = {
            "EXIF:DateTimeOriginal": datetime(2023, 5, 15, 10, 30, 0),
            "QuickTime:CreateDate": datetime(2023, 5, 15, 10, 30, 10),
            "XMP:DateCreated": datetime(2023, 5, 15, 10, 30, 5),
        }

        # Organize by levels
        fechas_nivel_1 = {"EXIF:DateTimeOriginal": fechas_todas["EXIF:DateTimeOriginal"]}
        fechas_nivel_2 = {"QuickTime:CreateDate": fechas_todas["QuickTime:CreateDate"]}
        fechas_nivel_3 = {"XMP:DateCreated": fechas_todas["XMP:DateCreated"]}

        # Validate level 1 date
        fecha_candidata = fechas_nivel_1["EXIF:DateTimeOriginal"]
        es_consistente = validador._validar_consistencia_fechas(
            fecha_candidata,
            fechas_todas,
            fechas_nivel_1
        )
        assert es_consistente is True

    def test_empty_fechas_dict_returns_no_date(self, config_validacion):
        """Test that empty fechas dict returns no_date (not ValueError)."""
        validador = DateValidator(config_validacion)
        # Empty dict should return (None, "no_date") - not raise ValueError
        fecha, razon = validador.validar_fecha_inteligente({})
        assert razon == "no_date"
        assert fecha is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
