"""Tests for the duplicate detection module."""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from sorter.duplicates import DuplicateDetector, FileInfo
from sorter.config import DeteccionDuplicadosConfig
from sorter.file_ops import FileOperations


@pytest.fixture
def config_duplicados():
    """Fixture for duplicate detection configuration."""
    return DeteccionDuplicadosConfig(
        activado=True,
        metodo="combinado",
        criterio_conservar="inteligente",
        umbral_tiempo_version=3600
    )


@pytest.fixture
def operaciones_mock():
    """Fixture to mock file operations."""
    mock = MagicMock(spec=FileOperations)
    mock.calcular_hash_completo.return_value = "mocked_hash_completo"
    mock.calcular_hash_rapido.return_value = "mocked_hash_rapido"
    return mock


@pytest.fixture
def detector(config_duplicados, operaciones_mock):
    """Fixture for detector with mocked dependencies."""
    detector = DuplicateDetector(config_duplicados)
    detector.operaciones = operaciones_mock
    detector.extractor = MagicMock()
    return detector


class TestDuplicateDetector:
    """Tests for DuplicateDetector."""

    def test_detection_disabled(self, config_duplicados):
        """Test when detection is disabled."""
        config_duplicados.activado = False
        detector = DuplicateDetector(config_duplicados)
        detector.registro_hashes = {"hash1": MagicMock()}

        es_dup, original, tipo = detector.es_duplicado(Path("/fake/path"), 100)
        assert es_dup is False
        assert original is None
        assert tipo == ""

    def test_no_size_candidates(self, detector):
        """Test when there are no candidates by size."""
        # Empty registry
        detector.registro_hashes = {}

        es_dup, original, tipo = detector.es_duplicado(Path("/fake/path"), 100)
        assert es_dup is False
        assert original is None
        assert tipo == ""

    def test_fast_hash_fails(self, detector, operaciones_mock):
        """Test when fast hash fails."""
        # Add a candidate
        info = FileInfo(
            ruta=Path("/origen/foto.jpg"),
            hash="hash1",
            hash_rapido="hash_rapido_1",
            fecha=datetime.now(),
            resolucion=(1920, 1080),
            tamano=1000
        )
        detector.registro_hashes["hash1"] = info

        # Fast hash fails
        operaciones_mock.calcular_hash_rapido.return_value = None

        es_dup, original, tipo = detector.es_duplicado(Path("/fake/path"), 1000)
        assert es_dup is False
        assert original is None
        assert tipo == ""

    def test_not_a_duplicate(self, detector, operaciones_mock):
        """Test when the file is not a duplicate."""
        # Complete hash different
        operaciones_mock.calcular_hash_rapido.return_value = "hash_rapido_1"
        operaciones_mock.calcular_hash_completo.return_value = "hash_completo_nuevo"

        info = FileInfo(
            ruta=Path("/origen/foto.jpg"),
            hash="otro_hash",
            hash_rapido="otro_hash_rapido",
            fecha=datetime.now(),
            resolucion=(1920, 1080),
            tamano=1000
        )
        detector.registro_hashes["otro_hash"] = info

        es_dup, original, tipo = detector.es_duplicado(Path("/fake/path"), 1000)
        assert es_dup is False
        assert original is None
        assert tipo == ""

    def test_exact_copy_duplicate(self, detector, operaciones_mock):
        """Test when the file is an exact duplicate."""
        operaciones_mock.calcular_hash_rapido.return_value = "hash_rapido_1"
        operaciones_mock.calcular_hash_completo.return_value = "hash_completo_1"

        fecha = datetime(2023, 1, 1, 10, 0, 0)
        info = FileInfo(
            ruta=Path("/origen/foto.jpg"),
            hash="hash_completo_1",
            hash_rapido="hash_rapido_1",
            fecha=fecha,
            resolucion=(1920, 1080),
            tamano=1000
        )
        detector.registro_hashes["hash_completo_1"] = info

        # Same timestamp (exact copy)
        detector.extractor.extraer_fecha_mas_antigua.return_value = "2023-01-01 10:00:00"
        detector.extractor.extraer_resolucion.return_value = (1920, 1080)

        es_dup, original, tipo = detector.es_duplicado(Path("/fake/path"), 1000)
        assert es_dup is True
        assert original is not None
        assert tipo == "copia_exacta"

    def test_higher_version_duplicate(self, detector, operaciones_mock):
        """Test when the file is a higher version."""
        operaciones_mock.calcular_hash_rapido.return_value = "hash_rapido_1"
        operaciones_mock.calcular_hash_completo.return_value = "hash_completo_1"

        fecha = datetime(2023, 1, 1, 10, 0, 0)
        info = FileInfo(
            ruta=Path("/origen/foto.jpg"),
            hash="hash_completo_1",
            hash_rapido="hash_rapido_1",
            fecha=fecha,
            resolucion=(1024, 768),
            tamano=1000
        )
        detector.registro_hashes["hash_completo_1"] = info

        # New version with better resolution (within time threshold)
        detector.extractor.extraer_fecha_mas_antigua.return_value = "2023-01-01 10:00:00"
        detector.extractor.extraer_resolucion.return_value = (3840, 2160)

        es_dup, original, tipo = detector.es_duplicado(Path("/fake/path"), 1000)
        assert es_dup is True
        assert tipo == "version_superior"


class TestDecidirCualConservar:
    """Tests for decidir_cual_conservar."""

    def test_higher_version_replaces(self, detector):
        """Test that higher version replaces the original."""
        original = FileInfo(
            ruta=Path("/origen/foto.jpg"),
            hash="hash1",
            hash_rapido="hash_rapido_1",
            fecha=datetime.now(),
            resolucion=(1024, 768),
            tamano=1000
        )

        should_replace = detector.decidir_cual_conservar(
            Path("/nuevo/foto.jpg"),
            original,
            "version_superior"
        )
        assert should_replace is True

    def test_lower_version_keeps(self, detector):
        """Test that lower version keeps the original."""
        original = FileInfo(
            ruta=Path("/origen/foto.jpg"),
            hash="hash1",
            hash_rapido="hash_rapido_1",
            fecha=datetime.now(),
            resolucion=(3840, 2160),
            tamano=1000
        )

        should_replace = detector.decidir_cual_conservar(
            Path("/nuevo/foto.jpg"),
            original,
            "version_inferior"
        )
        assert should_replace is False

    def test_exact_copy_keeps(self, detector):
        """Test that exact copy keeps the original."""
        original = FileInfo(
            ruta=Path("/origen/foto.jpg"),
            hash="hash1",
            hash_rapido="hash_rapido_1",
            fecha=datetime.now(),
            resolucion=(1920, 1080),
            tamano=1000
        )

        should_replace = detector.decidir_cual_conservar(
            Path("/nuevo/foto.jpg"),
            original,
            "copia_exacta"
        )
        assert should_replace is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
