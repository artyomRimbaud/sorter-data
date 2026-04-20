"""Main organizer - Orchestrates all modules."""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config import Configuracion
from .metadata import MetadataExtractor
from .file_ops import FileOperations
from .duplicates import DuplicateDetector, FileInfo
from .validator import DateValidator


class MainOrganizer:
    """Main organizer that orchestrates all modules."""

    MONTHS = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }

    def __init__(self, config: Configuracion, info_mode: bool = False):
        """
        Inicializa el organizador con la configuración.

        Args:
            config: Configuración completa del organizador
            info_mode: Si es True, solo recopila estadísticas sin mover archivos
        """
        self.config = config
        self.info_mode = info_mode

        # Initialize components
        self.extractor = MetadataExtractor(config)
        self.operations = FileOperations()
        self.detector = DuplicateDetector(config.duplicados)
        self.validator = DateValidator(config.validacion_fechas)

        # State
        self.stats = {
            "processed": 0,
            "moved": 0,
            "copied": 0,
            "total_duplicates": 0,
            "exact_copies": 0,
            "lower_versions": 0,
            "later_copies": 0,
            "no_date": 0,
            "suspicious_dates": 0,
            "validated_cross_check": 0,
            "screenshots_detected": 0,
            "errors": 0,
            "by_category": {}
        }
        self.duplicates: Dict[str, List[Tuple]] = {}  # category -> list of duplicates
        self.errors: List[str] = []

        # Store destination paths for simulation display
        self.simulation_destinations: Dict[Path, Tuple[Path, str]] = {}  # source -> (destination, category)

        # Timestamp for reports (new format: YYYY-MM-DD_HH-MM-SS)
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        # Determine report folder based on mode
        if self.info_mode:
            # Info mode: reports go inside source directory
            source = Path(self.config.origen[0]) if self.config.origen else Path("")
            self.report_folder = source / ".sorter_reports" / self.timestamp
        elif self.config.reportes.carpeta_reportes:
            # Config-specified folder
            self.report_folder = Path(self.config.reportes.carpeta_reportes)
        else:
            # Run mode: reports go inside destination directory
            dest = Path(self.config.destino_base)
            self.report_folder = dest / ".sorter_reports" / self.timestamp

        # Create reports directory if needed (only in non-simulation mode)
        if not self.config.operacion.modo_prueba:
            self.report_folder.mkdir(parents=True, exist_ok=True)

    def is_multimedia(self, category: str) -> bool:
        """Determina si una categoría es multimedia (organizada por fecha)."""
        return category in self.config.categorias_multimedia

    def get_category(self, file_path: Path) -> str:
        """Determina la categoría de un archivo."""
        extension = file_path.suffix.lower().lstrip('.')
        for category, extensions in self.config.categorias.items():
            if extension in extensions:
                return category
        return "Otros" if extension else "desconocido"

    def is_screenshot(self, file_path: Path) -> bool:
        """
        Detecta si un archivo es una captura de pantalla.

        Args:
            file_path: Ruta al archivo

        Returns:
            True si es una captura de pantalla
        """
        if not self.config.deteccion_capturas.activado:
            return False

        # Get the full path in lowercase for comparison
        full_path = str(file_path.parent).lower()

        # Search for keywords in the path
        keywords = self.config.deteccion_capturas.palabras_clave

        for keyword in keywords:
            if keyword.lower() in full_path:
                return True

        return False

    def get_final_category(
        self,
        file_path: Path
    ) -> Tuple[str, bool]:
        """
        Gets the final category of a file considering if it is a screenshot.

        Args:
            file_path: Path to the file

        Returns:
            Tuple(category_base, is_screenshot)
        """
        category_base = self.get_category(file_path)
        is_screenshot = self.is_screenshot(file_path)

        return (category_base, is_screenshot)

    def extract_file_date(self, file_path: Path) -> Optional[datetime]:
        """
        Extrae la fecha más antigua de los metadatos.

        Args:
            file_path: Ruta al archivo

        Returns:
            datetime o None si no existen fechas
        """
        all_dates = self.extractor.extraer_fechas_todas(file_path)

        if not all_dates:
            return None

        # Parse dates and find the oldest
        parsed_dates = []
        for label, value in all_dates.items():
            date = self._parse_date_string(value)
            if date:
                parsed_dates.append((label, date))

        if not parsed_dates:
            return None

        date_min = min(parsed_dates, key=lambda x: x[1])
        return date_min[1]

    def extract_all_dates(self, file_path: Path) -> Dict[str, datetime]:
        """
        Extrae TODAS las fechas del archivo organizadas por etiqueta.

        Args:
            file_path: Ruta al archivo

        Returns:
            Diccionario {etiqueta: datetime}
        """
        all_dates = self.extractor.extraer_fechas_todas(file_path)

        datetime_dates = {}
        for label, value in all_dates.items():
            date = self._parse_date_string(value)
            if date:
                datetime_dates[label] = date

        return datetime_dates

    def validate_date_intelligent(
        self,
        file_path: Path,
        category: str
    ) -> Tuple[Optional[datetime], str]:
        """
        Valida la fecha de un archivo usando validación cruzada.

        Args:
            file_path: Ruta al archivo
            category: Categoría del archivo

        Returns:
            Tuple(fecha_validada: Optional[datetime], razón: str)
            La razón puede ser: "válida", "sospechosa", "no_fecha"
        """
        # If not multimedia or validation disabled, use simple method
        if not self.config.validacion_fechas.activado:
            date = self.extract_file_date(file_path)
            return (date, "valid" if date else "no_date")

        if self.config.validacion_fechas.solo_multimedia:
            if category not in ["Fotos", "Videos"]:
                date = self.extract_file_date(file_path)
                return (date, "valid" if date else "no_date")

        # Extract all dates
        all_dates = self.extract_all_dates(file_path)

        if not all_dates:
            return (None, "no_date")

        # Validate using the validator
        validated_date, reason = self.validator.validar_fecha_inteligente(all_dates)

        if reason == "valid":
            self.stats["validated_cross_check"] += 1

        return (validated_date, reason)

    def _parse_date_string(self, date_string: str) -> Optional[datetime]:
        """Parse date in multiple formats."""
        if not isinstance(date_string, str):
            return None

        formats = [
            '%Y:%m:%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%Y:%m:%d',
            '%Y-%m-%d',
        ]

        for fmt in formats:
            try:
                clean_date = date_string.split('+')[0].split('-')[0].strip()
                return datetime.strptime(clean_date, fmt)
            except ValueError:
                continue
        return None

    def extract_resolution(self, file_path: Path) -> Optional[Tuple[int, int]]:
        """Extrae la resolución de imágenes/videos."""
        return self.extractor.extraer_resolucion(file_path)

    def generate_destination_path(
        self,
        file_path: Path,
        date: Optional[datetime],
        category: str,
        is_duplicate: bool = False,
        duplicate_type: str = "",
        is_suspicious: bool = False,
        is_screenshot: bool = False,
        original_path: Optional[Path] = None
    ) -> Path:
        """
        Genera la ruta de destino según la nueva estructura.

        Args:
            file_path: Ruta al archivo original
            date: Fecha del archivo (opcional)
            category: Categoría del archivo
            is_duplicate: Si el archivo es un duplicado
            duplicate_type: Tipo de duplicado
            is_suspicious: Si la fecha es sospechosa
            is_screenshot: Si es una captura de pantalla
            original_path: Ruta original (para duplicados)

        Returns:
            Ruta de destino
        """
        is_multimedia_cat = self.is_multimedia(category)
        multimedia_base = self.config.estructura.multimedia_base

        # ========== NON-MULTIMEDIA (documents, others) ==========
        if not is_multimedia_cat:
            if category == "Documentos":
                base_folder = Path(self.config.destino_base) \
                    / self.config.estructura.documentos_base
            else:
                base_folder = Path(self.config.destino_base) \
                    / self.config.estructura.otros_base

            # Handle duplicates for non-multimedia
            if is_duplicate:
                # For duplicates, go in a special subfolder
                # NOTE: We don't create the folder here - we just generate the path.
                # The folder will be created when actually moving/copying files in real mode.
                dup_folder = base_folder / self.config.estructura.carpeta_duplicados

                # Rename file with duplicate type
                name_base = file_path.stem
                extension = file_path.suffix
                suffixes = {
                    "copia_exacta": "_exact_copy",
                    "version_inferior": "_lower_version",
                    "version_superior": "_higher_version",
                    "copia_posterior": "_later_copy"
                }
                suffix = suffixes.get(duplicate_type, "_duplicate")
                name_with_suffix = f"{name_base}{suffix}{extension}"

                # Handle duplicate names
                counter = 0
                final_path = dup_folder / name_with_suffix

                while final_path.exists():
                    counter += 1
                    new_name = f"{name_base}{suffix}_{counter}{extension}"
                    final_path = dup_folder / new_name

                return final_path

            # Handle duplicate names for non-duplicates
            counter = 0
            final_path = base_folder / file_path.name

            while final_path.exists():
                counter += 1
                new_name = f"{file_path.stem}_{counter}{file_path.suffix}"
                final_path = base_folder / new_name

            return final_path

        # ========== MULTIMEDIA (photos, videos, audio) ==========
        type_lower = category.lower()
        dest_base = Path(self.config.destino_base)
        base_path = dest_base / multimedia_base / type_lower

        # Add "screenshots/" if it is a screenshot
        if is_screenshot and self.config.deteccion_capturas.como_subdirectorio:
            base_path = base_path / "screenshots"

        # If date is suspicious
        if is_suspicious:
            suspicious_folder = self.config.estructura.carpeta_sospechosas
            base_path = base_path / suspicious_folder

        # If no date
        if date is None:
            no_date_folder = self.config.estructura.carpeta_sin_fecha
            final_folder = base_path / no_date_folder
        else:
            # With date: year/month
            date_format = self.config.estructura.formato_fecha
            date_folder = date_format.format(
                year=date.year,
                month=date.month,
                month_name=self.MONTHS[date.month],
                day=date.day
            )
            final_folder = base_path / date_folder

        # If it is a duplicate, goes in the "duplicates/" folder INSIDE the month of the original
        if is_duplicate:
            # If we have the original path, use its folder
            if original_path and original_path.parent.exists():
                duplicate_folder = original_path.parent / self.config.estructura.carpeta_duplicados
            else:
                # Fallback: use the calculated folder
                duplicate_folder = final_folder / self.config.estructura.carpeta_duplicados

            final_folder = duplicate_folder

            # Rename file with duplicate type
            name_base = file_path.stem
            extension = file_path.suffix

            # Map types to suffixes
            suffixes = {
                "copia_exacta": "_exact_copy",
                "version_inferior": "_lower_version",
                "version_superior": "_higher_version",
                "copia_posterior": "_later_copy"
            }
            suffix = suffixes.get(duplicate_type, "_duplicate")
            name_with_suffix = f"{name_base}{suffix}{extension}"

            # Handle duplicate names
            counter = 0
            final_path = final_folder / name_with_suffix

            while final_path.exists():
                counter += 1
                new_name = f"{name_base}{suffix}_{counter}{extension}"
                final_path = final_folder / new_name

            return final_path

        # Normal file (not duplicate)
        counter = 0
        final_path = final_folder / file_path.name

        while final_path.exists():
            counter += 1
            new_name = f"{file_path.stem}_{counter}{file_path.suffix}"
            final_path = final_folder / new_name

        return final_path

    def process_file(self, file_path: Path) -> bool:
        """
        Procesa un archivo individual.

        Args:
            file_path: Ruta al archivo

        Returns:
            True si se procesó correctamente
        """
        try:
            # Skip if file no longer exists (e.g., broken symlink)
            if not file_path.exists():
                self.stats["errors"] += 1
                self.errors.append(f"Archivo no encontrado: {file_path}")
                return False

            # Get basic information
            category_base = self.get_category(file_path)
            category, is_screenshot = self.get_final_category(file_path)
            size = file_path.stat().st_size
            is_multimedia_cat = self.is_multimedia(category)

            # Mark if it is a screenshot
            if is_screenshot:
                self.stats["screenshots_detected"] += 1

            # If info mode, just process statistics without moving files
            if self.info_mode:
                self.stats["processed"] += 1
                self.stats["by_category"][category] = \
                    self.stats["by_category"].get(category, 0) + 1
                return True

            # === DUPLICATE DETECTION FOR ALL FILES ===
            # For multimedia files, validate date first for duplicate comparison
            date = None
            date_reason = "valid"

            if is_multimedia_cat or is_screenshot:
                date, date_reason = self.validate_date_intelligent(file_path, category_base)

            # Detect duplicates for ALL file types (not just multimedia)
            is_dup, original, dup_type = self.detector.es_duplicado(file_path, size)

            if is_dup:
                # Is duplicate - handle for all file types
                self.stats["total_duplicates"] += 1

                if dup_type == "copia_exacta":
                    self.stats["exact_copies"] += 1
                elif dup_type == "version_inferior":
                    self.stats["lower_versions"] += 1
                elif dup_type == "copia_posterior":
                    self.stats["later_copies"] += 1

                # Decide whether to replace the original
                replace = self.detector.decidir_cual_conservar(file_path, original, dup_type)

                if replace:
                    # Replace: move original to duplicates folder, place new one
                    if original.fecha:
                        dup_dest = self.generate_destination_path(
                            original.ruta, original.fecha, original.categoria,
                            True, dup_type, is_screenshot=original.es_captura,
                            original_path=original.ruta
                        )
                    else:
                        # For documents without date, use base category folder
                        dup_dest = self.generate_destination_path(
                            original.ruta, None, original.categoria,
                            True, dup_type, is_screenshot=original.es_captura,
                            original_path=original.ruta
                        )
                    # In simulation, move_or_copy_file returns True but doesn't actually move
                    # Still update registration for duplicate detection
                    if self.move_or_copy_file(original.ruta, dup_dest):
                        # Place the new one in the original location
                        destination = original.ruta
                        if self.move_or_copy_file(file_path, destination):
                            # Update register with new file info (needed for duplicate detection in simulation)
                            resolution = self.extract_resolution(file_path)
                            full_hash = self.operations.calcular_hash_completo(file_path)
                            hash_rapido = self.operations.calcular_hash_rapido(file_path)
                            if full_hash:
                                new_info = FileInfo(
                                    destination, full_hash, hash_rapido, date, resolution, size
                                )
                                new_info.categoria = category
                                new_info.es_captura = is_screenshot
                                self.detector.registro_hashes[full_hash] = new_info

                            self.duplicates.setdefault(category, []).append((destination, dup_dest, dup_type))
                else:
                    # Keep original: move duplicate to duplicates folder
                    if original.fecha:
                        destination = self.generate_destination_path(
                            file_path, original.fecha, original.categoria,
                            True, dup_type, is_screenshot=original.es_captura,
                            original_path=original.ruta
                        )
                    else:
                        destination = self.generate_destination_path(
                            file_path, None, original.categoria,
                            True, dup_type, is_screenshot=original.es_captura,
                            original_path=original.ruta
                        )
                    if self.move_or_copy_file(file_path, destination):
                        self.duplicates.setdefault(category, []).append((original.ruta, destination, dup_type))
                        # Also register the original in case future duplicates need it
                        # (In simulation, we don't actually move files but need registration for detection)
                        if not original.hash:
                            # Calculate hash for original if not already registered
                            orig_hash = self.operations.calcular_hash_completo(original.ruta)
                            if orig_hash:
                                orig_resolution = self.extract_resolution(original.ruta)
                                orig_hash_rapido = self.operations.calcular_hash_rapido(original.ruta)
                                if orig_hash not in self.detector.registro_hashes:
                                    orig_info = FileInfo(
                                        original.ruta, orig_hash, orig_hash_rapido, original.fecha, orig_resolution, original.tamano
                                    )
                                    orig_info.categoria = original.categoria
                                    orig_info.es_captura = original.es_captura
                                    self.detector.registro_hashes[orig_hash] = orig_info

                return True

            # === NOT A DUPLICATE - Process file ===

            # For multimedia, handle special date cases
            if is_multimedia_cat or is_screenshot:
                if date_reason == "no_date":
                    # No date, move to special folder
                    if is_screenshot and self.config.deteccion_capturas.como_subdirectorio:
                        type_lower = category.lower()
                        no_date_folder = self.config.estructura.carpeta_sin_fecha
                        base_dest = Path(self.config.destino_base) \
                            / self.config.estructura.multimedia_base / type_lower / "screenshots" / no_date_folder
                    else:
                        type_lower = category.lower()
                        no_date_folder = self.config.estructura.carpeta_sin_fecha
                        base_dest = Path(self.config.destino_base) \
                            / self.config.estructura.multimedia_base / type_lower / no_date_folder

                    # In simulation mode, update statistics but don't create directories or move files
                    if self.config.operacion.modo_prueba:
                        self.stats["by_category"][category] = \
                            self.stats["by_category"].get(category, 0) + 1
                        self.stats["processed"] += 1
                        self.stats["no_date"] += 1
                        return True

                    # Create directory only in real mode
                    base_dest.mkdir(parents=True, exist_ok=True)

                    counter = 0
                    final_path = base_dest / file_path.name
                    while final_path.exists():
                        counter += 1
                        final_path = base_dest / f"{file_path.stem}_{counter}{file_path.suffix}"

                    if self.move_or_copy_file(file_path, final_path):
                        self.stats["no_date"] += 1

                    return True

                if date_reason == "suspicious":
                    # Suspicious date, move to special folder
                    destination = self.generate_destination_path(
                        file_path, date, category,
                        is_suspicious=True, is_screenshot=is_screenshot
                    )

                    if self.move_or_copy_file(file_path, destination):
                        self.stats["processed"] += 1
                        if not self.config.operacion.modo_prueba:
                            self.stats["suspicious_dates"] += 1

                    return True

            # For non-multimedia or valid multimedia files, generate destination
            destination = self.generate_destination_path(
                file_path, date, category, is_screenshot=is_screenshot
            )

            # Calculate hash BEFORE moving the file (needed for both simulation and real mode)
            resolution = self.extract_resolution(file_path)
            full_hash = self.operations.calcular_hash_completo(file_path)
            hash_rapido = self.operations.calcular_hash_rapido(file_path)

            # In simulation mode, still update statistics but don't actually move files
            if self.config.operacion.modo_prueba:
                if full_hash:
                    # Register in hash index for duplicate detection
                    info = FileInfo(destination, full_hash, hash_rapido, date, resolution, size)
                    info.categoria = category
                    info.es_captura = is_screenshot
                    self.detector.registro_hashes[full_hash] = info

                self.stats["by_category"][category] = \
                    self.stats["by_category"].get(category, 0) + 1

                if self.config.operacion.modo_operacion == "mover":
                    self.stats["moved"] += 1
                else:
                    self.stats["copied"] += 1
                self.stats["processed"] += 1
            else:
                # Real mode: move/copy file and register
                if self.move_or_copy_file(file_path, destination):
                    if full_hash:
                        info = FileInfo(destination, full_hash, hash_rapido, date, resolution, size)
                        info.categoria = category
                        info.es_captura = is_screenshot
                        self.detector.registro_hashes[full_hash] = info

                    self.stats["by_category"][category] = \
                        self.stats["by_category"].get(category, 0) + 1

                    if self.config.operacion.modo_operacion == "mover":
                        self.stats["moved"] += 1
                    else:
                        self.stats["copied"] += 1
                    self.stats["processed"] += 1

            return True

        except Exception as e:
            self.errors.append(f"Error procesando {file_path.name}: {e}")
            self.stats["errors"] += 1
            return False

    def move_or_copy_file(self, source: Path, destination: Path) -> bool:
        """
        Mueve o copia el archivo según la configuración.

        Args:
            source: Ruta al archivo de origen
            destination: Ruta al destino

        Returns:
            True si la operación tuvo éxito
        """
        if self.config.operacion.modo_prueba:
            # En modo simulación, solo loguear pero no hacer nada
            return True

        # Usar copiar_archivo en modo copiar, mover_archivo en modo mover
        if self.config.operacion.modo_operacion == "copiar":
            success, error = self.operations.copiar_archivo(
                source, destination,
                self.config.operacion.verificar_integridad
            )
        else:
            success, error = self.operations.mover_archivo(
                source, destination,
                self.config.operacion.verificar_integridad
            )

        if not success and error:
            if self.config.operacion.modo_operacion == "copiar":
                self.errors.append(f"Error copiando {source.name}: {error}")
            else:
                self.errors.append(f"Error moviendo {source.name}: {error}")

        return success

    def generate_reports(self) -> None:
        """Genera todos los reportes configurados."""
        reports = []

        # Reporte TXT
        if self.config.reportes.generar_txt:
            path = self._generate_txt_report(self.report_folder / "report.txt")
            reports.append(path)

        # Reporte CSV
        if self.config.reportes.generar_csv:
            path = self._generate_csv_report(self.report_folder / "duplicates.csv")
            reports.append(path)

        # Log de errores
        if self.config.reportes.generar_log_errores and self.errors:
            path = self._generate_error_log(self.report_folder / "errors.log")
            reports.append(path)

        # Actualizar estadísticas con reportes generados
        self.stats["reports_generated"] = len(reports)

    def _generate_txt_report(self, path: Path) -> Path:
        """Genera reporte de texto."""
        with open(path, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("REPORTE DE ORGANIZACIÓN DE ARCHIVOS\n")
            f.write("=" * 70 + "\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Modo: {self.config.operacion.modo_operacion.upper()}\n")
            origen_str = self.config.origen[0] if self.config.origen else "N/A"
            f.write(f"Origen: {origen_str}\n")
            if len(self.config.origen) > 1:
                for orig in self.config.origen[1:]:
                    f.write(f"       + {orig}\n")
            f.write(f"Destino: {self.config.destino_base}\n\n")

            f.write("ESTADÍSTICAS GENERALES:\n")
            f.write(f"Archivos procesados: {self.stats['processed']:,}\n")

            if self.config.operacion.modo_operacion == 'mover':
                f.write(f"Archivos movidos: {self.stats['moved']:,}\n")
            else:
                f.write(f"Archivos copiados: {self.stats['copied']:,}\n")

            f.write(f"Duplicados encontrados: {self.stats['total_duplicates']:,}\n")
            f.write(f"   - Copias exactas: {self.stats['exact_copies']}\n")
            f.write(f"   - Versiones inferiores: {self.stats['lower_versions']}\n")
            f.write(f"   - Copias posteriores: {self.stats['later_copies']}\n")
            f.write(f"Sin fecha en metadatos: {self.stats['no_date']}\n")
            f.write(f"Fechas sospechosas: {self.stats['suspicious_dates']}\n")
            f.write(f"Fechas validadas (cruce): {self.stats['validated_cross_check']}\n")
            f.write(f"Capturas detectadas: {self.stats['screenshots_detected']}\n")
            f.write(f"Errores: {self.stats['errors']}\n\n")

            f.write("POR CATEGORÍA:\n")
            for cat, amount in sorted(self.stats['by_category'].items()):
                dups = sum(1 for d in self.duplicates.get(cat, []))
                f.write(f"  {cat}: {amount} archivos (duplicados: {dups})\n")

        return path

    def _generate_csv_report(self, path: Path) -> Path:
        """Genera reporte CSV de duplicados."""
        import csv

        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Tipo', 'Categoría', 'Archivo_Conservado', 'Archivo_Duplicado',
                'Razón', 'Fecha_Conservado', 'Fecha_Duplicado'
            ])

            for category, dups in self.duplicates.items():
                for original, duplicate, dup_type in dups:
                    writer.writerow([
                        dup_type, category, str(original), str(duplicate),
                        dup_type.replace('_', ' ').title(), '', ''
                    ])

        return path

    def _generate_error_log(self, path: Path) -> Path:
        """Genera log de errores."""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f"LOG DE ERRORES - {datetime.now()}\n")
            f.write("=" * 70 + "\n\n")
            for error in self.errors:
                f.write(f"{error}\n")

        return path

    def generate_simulation_tree(self) -> None:
        """Genera un árbol de directorios para la simulación."""
        print(f"\n{'='*70}")
        print("ESTRUCTURA DE DIRECTORIOS (SIMULACIÓN)")
        print(f"{'='*70}")

        # Get destination path
        dest_path = Path(self.config.destino_base)

        # Collect all directories and their file counts
        dir_info = {}  # dir_path -> {category: count}

        # Process each file to determine destination directories and counts
        for source, (destination, category) in self.simulation_destinations.items():
            # Count files by category for each directory
            # Also include all parent directories up to dest_path
            dir_path = destination.parent
            while True:
                if dir_path not in dir_info:
                    dir_info[dir_path] = {}
                dir_info[dir_path][category] = dir_info[dir_path].get(category, 0) + 1
                if dir_path == dest_path or dir_path == dir_path.parent:
                    break
                dir_path = dir_path.parent

        # Also include directories from existing files in destination
        existing_dirs = set()
        if dest_path.exists():
            for root, dirs, files in os.walk(dest_path):
                existing_dirs.add(Path(root))
                for d in dirs:
                    existing_dirs.add(Path(root) / d)

        # Add dest_path and all parent directories for destinations
        dest_dirs = set(dir_info.keys())
        all_dirs = existing_dirs.union(dest_dirs)
        all_dirs.add(dest_path)  # Ensure dest_path is the root of the tree

        # Build and print tree
        self._print_tree_simple(all_dirs, dir_info, dest_path)

        print(f"\n{'='*70}")

    def _print_tree_simple(
        self,
        all_dirs: set,
        dir_info: Dict,
        base_path: Path
    ) -> None:
        """Imprime el árbol de directorios con conteo de archivos."""

        # Build parent-child relationships
        children = {}
        for d in all_dirs:
            if d not in children:
                children[d] = []
            if d == base_path:
                continue
            parent = d.parent
            if parent not in children:
                children[parent] = []
            children[parent].append(d)

        # Sort children by name
        for parent in children:
            children[parent].sort(key=lambda x: str(x))

        def print_tree(node, prefix="", is_last=True):
            rel_path = node.relative_to(base_path)
            parts = rel_path.parts if rel_path.parts else ("",)
            indent = len(parts) - 1

            counts = dir_info.get(node, {})

            # Build category string
            cat_parts = []
            for cat, count in sorted(counts.items()):
                cat_parts.append(f"{count} {cat}")
            cat_str = f" ({', '.join(cat_parts)})" if cat_parts else ""

            if indent == 0:
                print(f"└─ {node.name}{cat_str}")
                new_prefix = "   "
            else:
                if is_last:
                    connector = "└─ "
                    child_prefix = "    "
                else:
                    connector = "├─ "
                    child_prefix = "│   "

                print(f"{prefix}{connector}{parts[-1]}{cat_str}")
                new_prefix = prefix + child_prefix

            if node in children and children[node]:
                for i, child in enumerate(children[node]):
                    child_is_last = i == len(children[node]) - 1
                    print_tree(child, new_prefix, child_is_last)

        # Start from base_path
        print_tree(base_path)

    def organize(self) -> None:
        """
        Función principal de organización.
        Procesa todos los archivos del origen según la configuración.
        """
        print(f"\n{'='*70}")
        print("ORGANIZADOR DE ARCHIVOS")
        print(f"{'='*70}")
        origen_str = self.config.origen[0] if self.config.origen else "N/A"
        print(f"[CARPETA] Origen: {origen_str}")
        if len(self.config.origen) > 1:
            for orig in self.config.origen[1:]:
                print(f"       + {orig}")
        print(f"[DISCO] Destino: {self.config.destino_base}")
        print(f"[LUPA] Recursivo: {'SÍ' if self.config.operacion.recursivo else 'NO'}")
        print(f"[] Modo: {self.config.operacion.modo_operacion.upper()}", end='')
        if self.config.operacion.modo_prueba:
            print(" (SIMULACIÓN - no se mueven archivos)", end='')
        print()
        print(f"[ALERTA] Detección de duplicados: {'SÍ' if self.config.duplicados.activado else 'NO'}")
        print(f"[ESCUDO] Verificar integridad: {'SÍ' if self.config.operacion.verificar_integridad else 'NO'}")
        print(f"{'='*70}\n")

        # Buscar archivos en todas las rutas de origen
        print(f"[LUPA] Buscando archivos...")
        files = []
        source_count = len(self.config.origen) if self.config.origen else 0
        if source_count == 0:
            print(f"[X] ERROR: No se especificaron directorios de origen")
            return

        for i, origen_path in enumerate(self.config.origen):
            source = Path(origen_path)
            if not source.exists():
                print(f"[X] ERROR: El directorio de origen no existe: {origen_path}")
                continue
            print(f"[{i+1}/{source_count}] Analizando: {origen_path}")

            if self.config.operacion.recursivo:
                for root, dirs, file_names in os.walk(source):
                    for file_name in file_names:
                        if not file_name.startswith('.'):
                            file_path = Path(root) / file_name
                            # Skip broken symlinks
                            if file_path.exists() or file_path.is_symlink() and file_path.resolve().exists():
                                files.append(file_path)
            else:
                files = [f for f in source.iterdir()
                           if f.is_file() and not f.name.startswith('.') and f.exists()]

        print(f"[GRAFICA] Archivos a procesar: {len(files)}\n")

        if len(files) == 0:
            print("! No se encontraron archivos")
            return

        # Reset simulation destinations if in simulation mode
        if self.config.operacion.modo_prueba:
            self.simulation_destinations = {}

        # Procesar archivos con barra de carga
        self._process_files_with_progress(files)

        # Generar estructura de simulación si estamos en modo simulación
        if self.config.operacion.modo_prueba:
            self.generate_simulation_tree()

        self.organize_final_steps()

    def _process_files_with_progress(self, files: list) -> None:
        """
        Procesa archivos mostrando una barra de carga.

        Args:
            files: Lista de rutas a archivos
        """
        total = len(files)
        # Ancho de la barra
        bar_width = 30
        # Longitud máxima del nombre de archivo a mostrar
        max_name_len = 30

        for i, file_path in enumerate(files, 1):
            # Calcular porcentaje
            percent = (i / total) * 100
            # Calcular cuántos caracteres de barra
            filled = int(bar_width * i // total)
            # Crear la barra
            bar = '█' * filled + '░' * (bar_width - filled)

            # Obtener nombre del archivo
            file_name = file_path.name
            if len(file_name) > max_name_len:
                file_name = "..." + file_name[-(max_name_len-3):]

            # Imprimir línea de progreso (se sobrescribe con \r)
            print(f"\r[PROCESANDO] {bar} {i}/{total} ({percent:5.1f}%) | {file_name} ", end='', flush=True)

            # Store simulation destination for tree building BEFORE processing
            # This allows us to capture the destination path before duplicates are processed
            if self.config.operacion.modo_prueba:
                category = self.get_category(file_path)
                category_base, is_screenshot = self.get_final_category(file_path)
                size = file_path.stat().st_size

                # First pass: detect if this is a duplicate (using size and hash)
                is_dup, original, dup_type = self.detector.es_duplicado(file_path, size)

                # Generate destination path (may be different for duplicates)
                if is_dup and original and original.fecha:
                    destination = self.generate_destination_path(
                        file_path, original.fecha, original.categoria,
                        True, dup_type, is_screenshot=is_screenshot, original_path=original.ruta
                    )
                else:
                    destination = self.generate_destination_path(
                        file_path, None, category, is_screenshot=is_screenshot
                    )
                self.simulation_destinations[file_path] = (destination, category)

            # Process the file - this updates stats but doesn't move files in simulation
            self.process_file(file_path)

        # Nueva línea al finalizar
        print()

    def organize_final_steps(self) -> None:
        """Genera reportes y muestra resumen final."""
        # Generar reportes (solo en modo real)
        if not self.config.operacion.modo_prueba:
            print(f"\n{'='*70}")
            print("Generando reportes...")
            self.generate_reports()

        # Mostrar resumen
        print(f"\n{'='*70}")
        print("RESUMEN FINAL")
        print(f"{'='*70}")
        print(f"[CHECK] Procesados: {self.stats['processed']:,}")

        if self.config.operacion.modo_operacion == 'mover':
            print(f"[PAQUETE] Movidos: {self.stats['moved']:,}")
        else:
            print(f"[PAQUETE] Copiados: {self.stats['copied']:,}")

        print(f"[ALERTA] Duplicados: {self.stats['total_duplicates']:,}")
        print(f"   - Copias exactas: {self.stats['exact_copies']}")
        print(f"   - Versiones inferiores: {self.stats['lower_versions']}")
        print(f"   - Copias posteriores: {self.stats['later_copies']}")
        print(f"! Sin fecha: {self.stats['no_date']}")
        print(f"[SOSPECHOSO] Fechas sospechosas: {self.stats['suspicious_dates']}")
        print(f"[CHECK] Fechas validadas (cruce): {self.stats['validated_cross_check']}")
        print(f"[CAPTURA] Capturas detectadas: {self.stats['screenshots_detected']}")
        print(f"[X] Errores: {self.stats['errors']}")
        print(f"{'='*70}\n")

