"""Tests for the file operations module."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib

from sorter.file_ops import FileOperations


class TestFileOperations:
    """Tests for FileOperations."""

    def test_full_hash_calculation(self, tmp_path):
        """Test that SHA256 hash is calculated correctly."""
        archivo = tmp_path / "test.txt"
        archivo.write_text("Hello, World!")

        hash_calc = FileOperations.calcular_hash_completo(archivo)
        hash_esperado = hashlib.sha256(b"Hello, World!").hexdigest()

        assert hash_calc == hash_esperado

    def test_fast_hash_calculation(self, tmp_path):
        """Test that fast hash (first bytes) is calculated."""
        archivo = tmp_path / "test.txt"
        archivo.write_text("Hello, World! This is a longer file.")

        hash_rapido = FileOperations.calcular_hash_rapido(archivo, bytes_leer=13)

        # Only the first 13 bytes
        hash_esperado = hashlib.sha256(b"Hello, World!").hexdigest()
        assert hash_rapido == hash_esperado

    def test_hash_nonexistent_file(self):
        """Test handling of non-existent file."""
        hash_rapido = FileOperations.calcular_hash_rapido(Path("/nonexistent/file.txt"))
        assert hash_rapido is None

    def test_create_directory(self, tmp_path):
        """Test that directories are created."""
        nuevo_dir = tmp_path / "nivel1" / "nivel2" / "nivel3"

        resultado = FileOperations.crear_directorio(nuevo_dir)

        assert resultado is True
        assert nuevo_dir.exists()
        assert nuevo_dir.is_dir()

    def test_directory_already_exists(self, tmp_path):
        """Test that it does not fail if directory already exists."""
        nuevo_dir = tmp_path / "ya_existe"
        nuevo_dir.mkdir()

        resultado = FileOperations.crear_directorio(nuevo_dir)

        assert resultado is True

    def test_move_file_successful(self, tmp_path):
        """Test that a file is moved correctly."""
        origen = tmp_path / "origen.txt"
        origen.write_text("Original content")

        destino = tmp_path / "destino" / "destino.txt"

        operaciones = FileOperations()
        exito, error = operaciones.mover_archivo(origen, destino, verificar_integridad=False)

        assert exito is True
        assert error is None
        assert not origen.exists()
        assert destino.exists()
        assert destino.read_text() == "Original content"

    def test_move_file_integrity_verification(self, tmp_path):
        """Test that integrity is verified during move."""
        origen = tmp_path / "origen.txt"
        contenido = "x" * 10000  # Larger file for hash
        origen.write_text(contenido)

        destino = tmp_path / "destino" / "destino.txt"

        operaciones = FileOperations()
        exito, error = operaciones.mover_archivo(origen, destino, verificar_integridad=True)

        assert exito is True
        assert destino.exists()
        assert destino.read_text() == contenido

    def test_move_file_source_not_exists(self, tmp_path):
        """Test handling of non-existent source."""
        destino = tmp_path / "destino.txt"

        operaciones = FileOperations()
        exito, error = operaciones.mover_archivo(Path("/nonexistent"), destino, verificar_integridad=False)

        assert exito is False
        assert error is not None

    def test_copy_file_successful(self, tmp_path):
        """Test that a file is copied correctly."""
        origen = tmp_path / "origen.txt"
        origen.write_text("Original content")

        destino = tmp_path / "destino" / "destino.txt"

        operaciones = FileOperations()
        exito, error = operaciones.copiar_archivo(origen, destino, verificar_integridad=False)

        assert exito is True
        assert error is None
        assert origen.exists()  # Original must exist
        assert destino.exists()
        assert destino.read_text() == "Original content"

    def test_simulate_move(self, tmp_path):
        """Test that move is simulated."""
        origen = tmp_path / "origen.txt"
        origen.write_text("Content")

        destino = tmp_path / "destino.txt"

        operaciones = FileOperations()
        exito, mensaje = operaciones.simular_mover(origen, destino)

        assert exito is True
        assert "[SIMULACI\xd3N]" in mensaje
        assert origen.name in mensaje
        assert destino.name in mensaje

    def test_simulate_copy(self, tmp_path):
        """Test that copy is simulated."""
        origen = tmp_path / "origen.txt"
        origen.write_text("Content")

        destino = tmp_path / "destino.txt"

        operaciones = FileOperations()
        exito, mensaje = operaciones.simular_copiar(origen, destino)

        assert exito is True
        assert "[SIMULACI\xd3N]" in mensaje
        assert "copiar\xeda" in mensaje


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
