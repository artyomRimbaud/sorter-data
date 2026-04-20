"""File organizer configuration."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


@dataclass
class ValidacionFechasConfig:
    """Configuration for date validation."""
    activado: bool = True
    solo_multimedia: bool = True
    fecha_minima_absoluta: str = "1990-01-01"
    fecha_maxima_relativa_anos: int = 1
    fechas_genericas: List[str] = field(default_factory=lambda: [
        "1970-01-01", "1980-01-01", "2000-01-01", "2001-01-01"
    ])
    requiere_validacion_cruzada: bool = True
    tolerancia_validacion_dias: int = 1
    minimo_fechas_coincidentes: int = 1
    fecha_minima_esperada: Optional[str] = "2018-01-01"
    accion_fecha_antes_esperada: str = "validar_cruzada"


@dataclass
class DeteccionCapturasConfig:
    """Configuration for screenshot detection."""
    activado: bool = True
    como_subdirectorio: bool = True
    palabras_clave: List[str] = field(default_factory=lambda: [
        "screenshot", "screenshots", "capturas", "captura de pantalla",
        "screen capture", "screencapture", "pantalla", "screen recording",
        "grabacion de pantalla"
    ])


@dataclass
class DeteccionDuplicadosConfig:
    """Configuration for duplicate detection."""
    activado: bool = True
    metodo: str = "combinado"
    criterio_conservar: str = "inteligente"
    umbral_tiempo_version: int = 3600


@dataclass
class EstructuraConfig:
    """Configuration for folder structure."""
    multimedia_base: str = "multimedia"
    documentos_base: str = "documentos"
    otros_base: str = "otros"
    carpeta_duplicados: str = "duplicados"
    carpeta_sospechosas: str = "fechas_sospechosas"
    carpeta_sin_fecha: str = "sin_fecha"
    formato_fecha: str = "{year}/{month:02d}-{month_name}"


@dataclass
class ReportesConfig:
    """Configuration for reports."""
    generar_csv: bool = True
    generar_txt: bool = True
    generar_log_errores: bool = True
    carpeta_reportes: Optional[str] = None


@dataclass
class LogsConfig:
    """Configuration for logs."""
    carpeta_logs: Optional[str] = None
    nivel: str = "INFO"


@dataclass
class OperacionConfig:
    """Configuration for operation."""
    recursivo: bool = True
    modo_prueba: bool = False
    modo_operacion: str = "mover"
    verificar_integridad: bool = True
    ignorar_grupo_file: bool = True


@dataclass
class Preset:
    """Configuration preset for file organization."""
    nombre: str
    modo: str
    inicio: Optional[List[str]] = None
    fin: Optional[str] = None
    activo: bool = True
    descripcion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert preset to dictionary for JSON serialization."""
        result = {
            "nombre": self.nombre,
            "modo": self.modo,
            "activo": self.activo
        }
        if self.inicio:
            result["inicio"] = self.inicio
        if self.fin:
            result["fin"] = self.fin
        if self.descripcion:
            result["descripcion"] = self.descripcion
        return result

    @classmethod
    def from_dict(cls, datos: Dict[str, Any]) -> "Preset":
        """Create a preset from a dictionary."""
        nombre = datos.get("nombre")
        if not nombre:
            raise ValueError("Preset must have a nombre (name)")

        modo = datos.get("modo")
        if modo not in ("mover", "copiar"):
            raise ValueError(f"Preset mode must be 'mover' or 'copiar', got '{modo}'")

        # Validate: either inicio or fin must be provided
        inicio = datos.get("inicio")
        fin = datos.get("fin")

        if not inicio and not fin:
            raise ValueError("Preset must have either 'inicio' (start) or 'fin' (end)")

        return cls(
            nombre=nombre,
            modo=modo,
            inicio=inicio if inicio else None,
            fin=fin if fin else None,
            activo=datos.get("activo", True),
            descripcion=datos.get("descripcion")
        )


@dataclass
class Configuracion:
    """Complete configuration for the organizer."""
    operacion: "OperacionConfig"
    estructura: "EstructuraConfig"
    duplicados: "DeteccionDuplicadosConfig"
    validacion_fechas: "ValidacionFechasConfig"
    deteccion_capturas: "DeteccionCapturasConfig"
    categorias: Dict[str, List[str]]
    categorias_multimedia: List[str]
    reportes: "ReportesConfig"
    logs: "LogsConfig"
    origen: List[str] = field(default_factory=list)
    destino_base: str = ""

    @classmethod
    def cargar_desde_json(cls, ruta: str) -> "Configuracion":
        """Load configuration from a JSON file."""
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)

        return cls.from_dict(datos)

    @staticmethod
    def _process_origen(origen_raw: Any) -> List[str]:
        """Process and normalize the origen field to ensure it's a list."""
        if isinstance(origen_raw, str):
            return [origen_raw]
        elif isinstance(origen_raw, list):
            return [str(item) for item in origen_raw]
        return []

    @classmethod
    def from_dict(cls, datos: Dict[str, Any]) -> "Configuracion":
        """Create an instance from a dictionary."""
        # Process categories
        categorias = {}
        for categoria, extensiones in datos.get("categorias", {}).items():
            categorias[categoria] = [e.lower().lstrip('.') for e in extensiones]

        # Process multimedia category lists
        categorias_multimedia = datos.get("categorias_multimedia", [])

        # Process origen - ensure it's always a list
        origen = cls._process_origen(datos.get("origen", []))

        # Process nested configurations
        return cls(
            operacion=OperacionConfig(
                recursivo=datos.get("operacion", {}).get("recursivo", True),
                modo_prueba=datos.get("operacion", {}).get("modo_prueba", False),
                modo_operacion=datos.get("operacion", {}).get("modo_operacion", "mover"),
                verificar_integridad=datos.get("operacion", {}).get("verificar_integridad", True),
                ignorar_grupo_file=datos.get("operacion", {}).get("ignorar_grupo_file", True)
            ),
            estructura=EstructuraConfig(
                multimedia_base=datos.get("estructura", {}).get("multimedia_base", "multimedia"),
                documentos_base=datos.get("estructura", {}).get("documentos_base", "documentos"),
                otros_base=datos.get("estructura", {}).get("otros_base", "otros"),
                carpeta_duplicados=datos.get("estructura", {}).get("carpeta_duplicados", "duplicados"),
                carpeta_sospechosas=datos.get("estructura", {}).get("carpeta_sospechosas", "fechas_sospechosas"),
                carpeta_sin_fecha=datos.get("estructura", {}).get("carpeta_sin_fecha", "sin_fecha"),
                formato_fecha=datos.get("estructura", {}).get("formato_fecha", "{year}/{month:02d}-{month_name}")
            ),
            duplicados=DeteccionDuplicadosConfig(
                activado=datos.get("duplicados", {}).get("activado", True),
                metodo=datos.get("duplicados", {}).get("metodo", "combinado"),
                criterio_conservar=datos.get("duplicados", {}).get("criterio_conservar", "inteligente"),
                umbral_tiempo_version=datos.get("duplicados", {}).get("umbral_tiempo_version", 3600)
            ),
            validacion_fechas=ValidacionFechasConfig(
                activado=datos.get("validacion_fechas", {}).get("activado", True),
                solo_multimedia=datos.get("validacion_fechas", {}).get("solo_multimedia", True),
                fecha_minima_absoluta=datos.get("validacion_fechas", {}).get("fecha_minima_absoluta", "1990-01-01"),
                fecha_maxima_relativa_anos=datos.get("validacion_fechas", {}).get("fecha_maxima_relativa_anos", 1),
                fechas_genericas=datos.get("validacion_fechas", {}).get("fechas_genericas", [
                    "1970-01-01", "1980-01-01", "2000-01-01", "2001-01-01"
                ]),
                requiere_validacion_cruzada=datos.get("validacion_fechas", {}).get("requiere_validacion_cruzada", True),
                tolerancia_validacion_dias=datos.get("validacion_fechas", {}).get("tolerancia_validacion_dias", 1),
                minimo_fechas_coincidentes=datos.get("validacion_fechas", {}).get("minimo_fechas_coincidentes", 1),
                fecha_minima_esperada=datos.get("validacion_fechas", {}).get("fecha_minima_esperada", "2018-01-01"),
                accion_fecha_antes_esperada=datos.get("validacion_fechas", {}).get("accion_fecha_antes_esperada", "validar_cruzada")
            ),
            deteccion_capturas=DeteccionCapturasConfig(
                activado=datos.get("deteccion_capturas", {}).get("activado", True),
                como_subdirectorio=datos.get("deteccion_capturas", {}).get("como_subdirectorio", True),
                palabras_clave=datos.get("deteccion_capturas", {}).get("palabras_clave", [])
            ),
            categorias=categorias,
            categorias_multimedia=categorias_multimedia,
            reportes=ReportesConfig(
                generar_csv=datos.get("reportes", {}).get("generar_csv", True),
                generar_txt=datos.get("reportes", {}).get("generar_txt", True),
                generar_log_errores=datos.get("reportes", {}).get("generar_log_errores", True),
                carpeta_reportes=datos.get("reportes", {}).get("carpeta_reportes")
            ),
            logs=LogsConfig(
                carpeta_logs=datos.get("logs", {}).get("carpeta_logs"),
                nivel=datos.get("logs", {}).get("nivel", "INFO")
            ),
            origen=origen,
            destino_base=datos.get("destino_base", "")
        )

    def obtener_origen(self) -> str:
        """Get the source path for the current configuration."""
        return self.origen[0] if self.origen else ""

    def obtener_destino_base(self) -> str:
        """Get the base destination path for the current configuration."""
        return self.destino_base


def get_default_preset_path() -> Path:
    """Get the default presets directory path."""
    home = Path.home()
    return home / ".config" / "sorter-data" / "presets"


def create_default_config() -> Dict[str, Any]:
    """Create a default configuration dictionary."""
    return {
        "operacion": {
            "recursivo": True,
            "modo_prueba": False,
            "modo_operacion": "mover",
            "verificar_integridad": True,
            "ignorar_grupo_file": True
        },
        "estructura": {
            "multimedia_base": "multimedia",
            "documentos_base": "documentos",
            "otros_base": "otros",
            "carpeta_duplicados": "duplicados",
            "carpeta_sospechosas": "fechas_sospechosas",
            "carpeta_sin_fecha": "sin_fecha",
            "formato_fecha": "{year}/{month:02d}-{month_name}"
        },
        "duplicados": {
            "activado": True,
            "metodo": "combinado",
            "criterio_conservar": "inteligente",
            "umbral_tiempo_version": 3600
        },
        "validacion_fechas": {
            "activado": True,
            "solo_multimedia": True,
            "fecha_minima_absoluta": "1990-01-01",
            "fecha_maxima_relativa_anos": 1,
            "fechas_genericas": ["1970-01-01", "1980-01-01", "2000-01-01", "2001-01-01"],
            "requiere_validacion_cruzada": True,
            "tolerancia_validacion_dias": 1,
            "minimo_fechas_coincidentes": 1,
            "fecha_minima_esperada": "2018-01-01",
            "accion_fecha_antes_esperada": "validar_cruzada"
        },
        "deteccion_capturas": {
            "activado": True,
            "como_subdirectorio": True,
            "palabras_clave": [
                "screenshot", "screenshots", "capturas", "captura de pantalla",
                "screen capture", "screencapture", "pantalla", "screen recording",
                "grabacion de pantalla"
            ]
        },
        "categorias": {
            "Fotos": ["dng", "jpeg", "jpg", "png", "heic", "raw", "cr2", "nef", "arw"],
            "Videos": ["mp4", "mkv", "mov", "avi", "m4v", "mts", "3gp", "webm"],
            "Audios": ["mp3", "flac", "m4a", "wav", "aac", "ogg", "wma", "opus"],
            "Documentos": ["pdf", "docx", "doc", "xlsx", "xls", "pptx", "txt", "odt"]
        },
        "categorias_multimedia": ["Fotos", "Videos", "Audios"],
        "reportes": {
            "generar_csv": True,
            "generar_txt": True,
            "generar_log_errores": True
        },
        "logs": {
            "carpeta_logs": None,
            "nivel": "INFO"
        }
    }
