"""File date validation."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .config import ValidacionFechasConfig
from .metadata import MetadataExtractor


class DateValidator:
    """Validates multimedia file dates using cross-validation logic."""

    def __init__(self, config: ValidacionFechasConfig):
        """
        Initializes the validator with the configuration.

        Args:
            config: Date validation configuration
        """
        self.config = config
        self.extractor = MetadataExtractor(None)  # The extractor will be injected

    def validar_fecha_inteligente(
        self,
        todas_fechas: Dict[str, datetime],
        requerir_validacion_cruzada: Optional[bool] = None
    ) -> Tuple[Optional[datetime], str]:
        """
        Validates a file date using cross-validation.

        Args:
            todas_fechas: Dictionary {label: date} with all dates from the file
            requerir_validacion_cruzada: If None, uses the configuration

        Returns:
            Tuple(validated_date: Optional[datetime], reason: str)
            The reason can be: "valid", "suspicious", "no_date"
        """
        if not todas_fechas:
            return (None, "no_date")

        # Configuration
        fecha_min_abs = datetime.strptime(
            self.config.fecha_minima_absoluta, "%Y-%m-%d"
        )
        fecha_max_abs = datetime.now() + timedelta(
            days=365 * self.config.fecha_maxima_relativa_anos
        )
        fechas_genericas = [
            datetime.strptime(f, "%Y-%m-%d")
            for f in self.config.fechas_genericas
        ]
        fecha_min_esperada: Optional[datetime] = None
        if self.config.fecha_minima_esperada:
            fecha_min_esperada = datetime.strptime(
                self.config.fecha_minima_esperada, "%Y-%m-%d"
            )

        # Organize dates by hierarchy level
        fechas_por_nivel = self._organizar_fechas_por_nivel(todas_fechas)

        # Try to validate for each level
        for nivel, fechas_nivel in enumerate(fechas_por_nivel):
            if not fechas_nivel:
                continue

            # Take the oldest date from the level
            fecha_candidata = min(fechas_nivel.values())

            # Validate that it is not an absolute odd date
            if fecha_candidata < fecha_min_abs:
                continue  # Date before 1990, move to next level

            if fecha_candidata > fecha_max_abs:
                continue  # Date in the future, move to next level

            # Validate that it is not a generic date
            es_generica = any(
                abs((fecha_candidata - fg).total_seconds()) < 86400
                for fg in fechas_genericas
            )
            if es_generica:
                continue  # Generic date, move to next level

            # If the date is before the expected date, requires cross-validation
            requiere_validacion = False
            if fecha_min_esperada and fecha_candidata < fecha_min_esperada:
                if self.config.accion_fecha_antes_esperada == "validar_cruzada":
                    requiere_validacion = True
                elif self.config.accion_fecha_antes_esperada == "rechazar":
                    continue  # Reject and move to next level

            # Cross-validation
            validacion_cruzada = (
                requerir_validacion_cruzada
                if requerir_validacion_cruzada is not None
                else self.config.requiere_validacion_cruzada
            )

            if validacion_cruzada or requiere_validacion:
                es_consistente = self._validar_consistencia_fechas(
                    fecha_candidata, todas_fechas, fechas_nivel
                )

                if es_consistente:
                    return (fecha_candidata, "valid")
                elif requiere_validacion:
                    # Date < expected without cross-validation
                    continue  # Move to next level
            else:
                # No cross-validation required
                return (fecha_candidata, "valid")

        # No valid date found
        # Return the least bad one to mark it as suspicious
        if todas_fechas:
            fecha_menos_mala = min(todas_fechas.values())
        else:
            fecha_menos_mala = None
        return (fecha_menos_mala, "suspicious")

    def _organizar_fechas_por_nivel(
        self,
        todas_fechas: Dict[str, datetime]
    ) -> List[Dict[str, datetime]]:
        """
        Organizes dates by hierarchy level.

        Args:
            todas_fechas: Dictionary {label: date}

        Returns:
            List of dictionaries, one per level
        """
        fechas_por_nivel: List[Dict[str, datetime]] = [
            dict() for _ in range(len(MetadataExtractor.DATE_HIERARCHY))
        ]

        for etiqueta, fecha in todas_fechas.items():
            for nivel, etiquetas_nivel in enumerate(MetadataExtractor.DATE_HIERARCHY):
                if any(etiq in etiqueta for etiq in etiquetas_nivel):
                    fechas_por_nivel[nivel][etiqueta] = fecha
                    break

        return fechas_por_nivel

    def _validar_consistencia_fechas(
        self,
        fecha_candidata: datetime,
        todas_fechas: Dict[str, datetime],
        fechas_mismo_nivel: Dict[str, datetime]
    ) -> bool:
        """
        Validates if the candidate date is consistent with other dates in the file.

        Args:
            fecha_candidata: The date being validated
            todas_fechas: All dates from the file
            fechas_mismo_nivel: Dates from the same level to ignore

        Returns:
            True if at least minimo_fechas_coincidentes dates from ANOTHER level match
        """
        tolerancia = timedelta(
            days=self.config.tolerancia_validacion_dias
        )
        minimo_coincidencias = self.config.minimo_fechas_coincidentes

        coincidencias = 0

        for etiqueta, fecha in todas_fechas.items():
            # Ignore dates from the same level
            if etiqueta in fechas_mismo_nivel:
                continue

            # Calculate difference
            diferencia = abs((fecha - fecha_candidata).total_seconds())

            if diferencia <= tolerancia.total_seconds():
                coincidencias += 1

                if coincidencias >= minimo_coincidencias:
                    return True

        return False


def validate_date(
    todas_fechas: Dict[str, datetime],
    config: ValidacionFechasConfig
) -> Tuple[Optional[datetime], str]:
    """
    Helper function to validate a date using the configuration.

    Args:
        todas_fechas: Dictionary {label: date}
        config: Validation configuration

    Returns:
        Tuple(validated_date, reason)
    """
    validador = DateValidator(config)
    return validador.validar_fecha_inteligente(todas_fechas)


def is_suspicious_date(
    fecha: datetime,
    config: ValidacionFechasConfig
) -> bool:
    """
    Checks if a date is suspicious (generic or out of range).

    Args:
        fecha: The date to check
        config: Validation configuration

    Returns:
        True if the date is suspicious
    """
    fecha_min_abs = datetime.strptime(
        config.fecha_minima_absoluta, "%Y-%m-%d"
    )
    fecha_max_abs = datetime.now() + timedelta(
        days=365 * config.fecha_maxima_relativa_anos
    )
    fechas_genericas = [
        datetime.strptime(f, "%Y-%m-%d")
        for f in config.fechas_genericas
    ]

    # Verify absolute range
    if fecha < fecha_min_abs or fecha > fecha_max_abs:
        return True

    # Verify if it is a generic date
    if any(
        abs((fecha - fg).total_seconds()) < 86400
        for fg in fechas_genericas
    ):
        return True

    return False
