"""Tests for the metadata extraction module."""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
import json

from sorter.metadata import MetadataExtractor
from sorter.config import Configuracion


@pytest.fixture
def config_mock():
    """Fixture for mocked configuration."""
    config = MagicMock(spec=Configuracion)
    config.validacion_fechas = MagicMock()
    return config


@pytest.fixture
def extractor(config_mock):
    """Fixture for metadata extractor."""
    extractor = MetadataExtractor(config_mock)
    return extractor


class TestMetadataExtractor:
    """Tests for MetadataExtractor."""

    def test_exiftool_check_successful(self, extractor):
        """Test when exiftool is installed."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "11.18\n"

            resultado = extractor.verificar_exiftool()

            assert resultado is True
            assert extractor._exiftool_verified is True

    def test_exiftool_check_fails(self, extractor):
        """Test when exiftool is not installed."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()

            resultado = extractor.verificar_exiftool()

            assert resultado is False

    def test_extract_all_dates_successful(self, extractor):
        """Test when dates are extracted correctly."""
        datos_json = json.dumps([{
            "EXIF:DateTimeOriginal": "2023:05:15 10:30:00",
            "QuickTime:CreateDate": "2023-05-15 10:30:00",
            "File:FileModifyDate": "2023:05:15 12:00:00"
        }])

        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = datos_json
            mock_run.return_value.stderr = ""

            resultado = extractor.extraer_fechas_todas(Path("/fake/foto.jpg"))

            assert "EXIF:DateTimeOriginal" in resultado
            assert resultado["EXIF:DateTimeOriginal"] == "2023:05:15 10:30:00"

    def test_extract_all_dates_fails(self, extractor):
        """Test when exiftool fails."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "Error"

            resultado = extractor.extraer_fechas_todas(Path("/fake/foto.jpg"))

            assert resultado == {}

    def test_extract_resolution_successful(self, extractor):
        """Test when resolution is extracted correctly."""
        datos_json = json.dumps([{
            "ImageWidth": 1920,
            "ImageHeight": 1080
        }])

        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = datos_json

            resultado = extractor.extraer_resolucion(Path("/fake/foto.jpg"))

            assert resultado == (1920, 1080)

    def test_extract_resolution_fails(self, extractor):
        """Test when exiftool fails for resolution."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1

            resultado = extractor.extraer_resolucion(Path("/fake/foto.jpg"))

            assert resultado is None

    def test_extract_organized_dates(self, extractor):
        """Test that dates are organized by hierarchy."""
        fechas = {
            "EXIF:DateTimeOriginal": "2023-05-15 10:30:00",
            "QuickTime:CreateDate": "2023-05-15 10:30:00",
            "XMP:DateCreated": "2023-05-15 10:30:00",
        }

        with patch.object(extractor, 'extraer_fechas_todas', return_value=fechas):
            resultado = extractor.extraer_fechas_organizadas(Path("/fake/foto.jpg"))

            # Should have 4 levels
            assert len(resultado) == 4

            # Level 1 (EXIF) should have a date
            assert len(resultado[0]) >= 1

    def test_parse_date_string_successful(self, extractor):
        """Test when a date is parsed correctly."""
        fecha_str = "2023:05:15 10:30:00+02:00"
        resultado = extractor._parsear_fecha_string(fecha_str)

        assert resultado == datetime(2023, 5, 15, 10, 30, 0)

    def test_parse_date_string_different_format(self, extractor):
        """Test with different date format."""
        fecha_str = "2023-05-15 10:30:00"
        resultado = extractor._parsear_fecha_string(fecha_str)

        assert resultado == datetime(2023, 5, 15, 10, 30, 0)

    def test_parse_date_string_invalid(self, extractor):
        """Test with invalid date."""
        resultado = extractor._parsear_fecha_string("invalid_date")
        assert resultado is None

    def test_parse_date_string_not_string(self, extractor):
        """Test when input is not a string."""
        resultado = extractor._parsear_fecha_string(12345)
        assert resultado is None


class TestMetadataIntegration:
    """Integration tests for the extractor."""

    def test_extract_oldest_date(self, extractor):
        """Test that returns the oldest date."""
        fechas = {
            "EXIF:DateTimeOriginal": "2023-05-15 10:30:00",
            "QuickTime:CreateDate": "2023-06-20 14:00:00",
            "XMP:DateCreated": "2023-01-01 08:00:00",  # Oldest
        }

        with patch.object(extractor, 'extraer_fechas_todas', return_value=fechas):
            with patch.object(extractor, '_parsear_fecha_string') as mock_parse:
                def parse_mock(val):
                    mapping = {
                        "2023-05-15 10:30:00": datetime(2023, 5, 15, 10, 30, 0),
                        "2023-06-20 14:00:00": datetime(2023, 6, 20, 14, 0, 0),
                        "2023-01-01 08:00:00": datetime(2023, 1, 1, 8, 0, 0),
                    }
                    return mapping.get(val)

                mock_parse.side_effect = parse_mock

                resultado = extractor.extraer_fecha_mas_antigua(Path("/fake/foto.jpg"))

                # Should be the oldest: 2023-01-01
                assert "2023-01-01" in resultado

    def test_extract_oldest_date_empty(self, extractor):
        """Test when there are no dates."""
        with patch.object(extractor, 'extraer_fechas_todas', return_value={}):
            resultado = extractor.extraer_fecha_mas_antigua(Path("/fake/foto.jpg"))
            assert resultado is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
