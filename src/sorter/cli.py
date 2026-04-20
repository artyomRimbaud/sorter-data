#!/usr/bin/env python3
"""Punto de entrada CLI para el organizador de archivos sorter-data."""

import argparse
import sys
from pathlib import Path

from sorter.config import Configuracion, create_default_config
from sorter.organizer import MainOrganizer
from sorter.preset_manager import PresetManager, PresetManagerError, PresetValidationError, PresetNotFoundError


def cmd_run(args):
    """Ejecutar el comando run en modo mover o copiar."""
    try:
        # Crear configuración por defecto
        config_data = create_default_config()
        config = Configuracion.from_dict(config_data)

        # Establecer modo de operación
        if args.mode == "copy":
            config.operacion.modo_operacion = "copiar"
        else:
            config.operacion.modo_operacion = "mover"

        # Establecer origen y destino desde los argumentos CLI
        # Analizar rutas de origen separadas por comas
        start_paths = [Path(p.strip()) for p in args.start.split(",")]
        end_path = Path(args.end).expanduser()

        # Validar y crear rutas de origen si es necesario
        validated_start_paths = []
        for sp in start_paths:
            if not sp.exists():
                create = input(f"El directorio '{sp}' no existe. ¿Crearlo? [s/n]: ")
                if create.strip().lower() == 's':
                    sp.mkdir(parents=True, exist_ok=True)
                    print(f"Directorio creado: {sp}")
                else:
                    print("Operación abortada.")
                    sys.exit(1)
            validated_start_paths.append(sp)
        start_paths = validated_start_paths

        # Validar y crear ruta de destino si es necesario
        if not end_path.exists():
            create = input(f"El directorio '{end_path}' no existe. ¿Crearlo? [s/n]: ")
            if create.strip().lower() == 's':
                end_path.mkdir(parents=True, exist_ok=True)
                print(f"Directorio creado: {end_path}")
            else:
                print("Operación abortada.")
                sys.exit(1)

        # Establecer rutas en la configuración
        config.origen = [str(sp) for sp in start_paths] if start_paths else []
        config.destino_base = str(end_path)

        # Establecer modo simulación si se especificó
        if args.simulation:
            config.operacion.modo_prueba = True

        # Crear y iniciar organizador
        organizer = MainOrganizer(config)
        organizer.organize()

    except KeyboardInterrupt:
        print("\n\nOperación cancelada por el usuario.")
        sys.exit(130)
    except ValueError as e:
        print(f"\nERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def cmd_preset(args):
    """Ejecutar el comando preset (create/list/run/delete)."""
    try:
        from sorter.config import get_default_preset_path

        presets_dir = get_default_preset_path()
        manager = PresetManager(presets_dir)

        # Manejar --create con parámetros requeridos
        if args.create:
            if not args.run:
                print("ERROR: --create requiere --run con modo 'move' o 'copy'")
                sys.exit(1)

            # Verificar si tenemos start y end
            if not args.start and not args.end:
                print("ERROR: --create requiere --start o --end")
                sys.exit(1)

            # Obtener rutas de origen (separadas por comas)
            start_paths = []
            if args.start:
                start_paths = [Path(p.strip()) for p in args.start.split(",")]
            else:
                # Pedir ruta de origen interactivamente
                start_input = input("Directorio(s) de origen: ")
                start_paths = [Path(p.strip()) for p in start_input.split(",") if p.strip()]

            # Obtener ruta de destino
            if args.end:
                end_path = Path(args.end).expanduser()
            else:
                # Pedir ruta de destino interactivamente
                end_input = input("Directorio de destino: ")
                end_path = Path(end_input.strip()).expanduser()

            # Validar y crear rutas de origen si es necesario
            validated_start_paths = []
            for sp in start_paths:
                if not sp.exists():
                    create = input(f"El directorio '{sp}' no existe. ¿Crearlo? [s/n]: ")
                    if create.strip().lower() == 's':
                        sp.mkdir(parents=True, exist_ok=True)
                        print(f"Directorio creado: {sp}")
                    else:
                        print("Creación de preset abortada.")
                        sys.exit(1)
                validated_start_paths.append(sp)

            # Validar y crear ruta de destino si es necesario
            if not end_path.exists():
                create = input(f"El directorio '{end_path}' no existe. ¿Crearlo? [s/n]: ")
                if create.strip().lower() == 's':
                    end_path.mkdir(parents=True, exist_ok=True)
                    print(f"Directorio creado: {end_path}")
                else:
                    print("Creación de preset abortada.")
                    sys.exit(1)

            start_paths = validated_start_paths

            # Crear preset
            preset = manager.create(
                nombre=args.create,
                modo=args.run,
                inicio=[str(sp) for sp in start_paths],
                fin=str(end_path)
            )
            print(f"Preset '{preset.nombre}' creado correctamente")
            return

        # Manejar subcomandos de acción de preset
        preset_name = args.preset_name
        preset_action = args.preset_action

        if not preset_name:
            # No se especificó nombre de preset - listar todos los presets
            presets = manager.list()
            if not presets:
                print("No se encontraron presets")
                return

            print("Presets disponibles:")
            for p in presets:
                mode_desc = "mover" if p.modo == "mover" else "copiar"
                start_str = ", ".join(p.inicio) if p.inicio else "N/A"
                end_str = p.fin or "N/A"
                status = "activo" if p.activo else "inactivo"
                print(f"  {p.nombre} [{status}] - {mode_desc}: {start_str} -> {end_str}")
            return

        # Manejar acciones en preset específico
        if preset_action == "run" or preset_action is None:
            # Ejecutar el preset (acción por defecto si no se especifica acción)
            run_preset(manager, preset_name, simulation=False)
        elif preset_action == "simulation":
            # Alias para run con simulación
            run_preset(manager, preset_name, simulation=True)
        elif preset_action == "delete":
            # Eliminar el preset
            try:
                manager.delete(preset_name)
                print(f"Preset '{preset_name}' eliminado correctamente")
            except PresetManagerError as e:
                print(f"ERROR: {e}")
                sys.exit(1)
        elif preset_action == "list":
            # Esto no debería suceder con la configuración del parser, pero manejarlo
            print("Usa 'sorter preset' para listar todos los presets")
        else:
            # Ejecutar con bandera de simulación desde args
            simulation = getattr(args, 'simulation', False)
            run_preset(manager, preset_name, simulation=simulation)

    except KeyboardInterrupt:
        print("\n\nOperación cancelada por el usuario.")
        sys.exit(130)
    except PresetValidationError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    except PresetManagerError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def run_preset(manager: PresetManager, preset_name: str, simulation: bool = False):
    """Ejecutar un preset con el nombre dado."""
    try:
        preset = manager.read(preset_name)
    except PresetNotFoundError:
        print(f"ERROR: Preset '{preset_name}' no encontrado")
        sys.exit(1)

    # Crear configuración por defecto
    config_data = create_default_config()
    config = Configuracion.from_dict(config_data)

    # Sobrescribir rutas desde el preset
    if preset.inicio:
        config.origen = [str(Path(p)) for p in preset.inicio]
    else:
        config.origen = []
    if preset.fin:
        config.destino_base = str(Path(preset.fin).expanduser())

    # Establecer modo de operación
    if preset.modo == "copiar":
        config.operacion.modo_operacion = "copiar"
    else:
        config.operacion.modo_operacion = "mover"

    # Establecer modo simulación
    if simulation:
        config.operacion.modo_prueba = True

    # Crear y iniciar organizador
    organizer = MainOrganizer(config)
    organizer.organize()


def cmd_info(args):
    """Ejecutar el comando info para analizar el directorio de origen."""
    try:
        # Crear configuración por defecto
        config_data = create_default_config()
        config = Configuracion.from_dict(config_data)

        # Establecer origen desde los argumentos CLI - soportar rutas separadas por comas
        start_paths = [Path(p.strip()) for p in args.start.split(",")]

        # Validar y crear rutas de origen si es necesario
        validated_start_paths = []
        for sp in start_paths:
            if not sp.exists():
                create = input(f"El directorio '{sp}' no existe. ¿Crearlo? [s/n]: ")
                if create.strip().lower() == 's':
                    sp.mkdir(parents=True, exist_ok=True)
                    print(f"Directorio creado: {sp}")
                else:
                    print("Operación abortada.")
                    sys.exit(1)
            validated_start_paths.append(sp)
        start_paths = validated_start_paths

        # Usar primera ruta como fuente principal, establecer destino a la primera ruta para modo info
        config.origen = [str(start_paths[0])]
        config.destino_base = str(start_paths[0])

        # Establecer modo info (solo estadísticas, sin operaciones de archivos)
        organizer = MainOrganizer(config, info_mode=True)
        organizer.organize()

    except KeyboardInterrupt:
        print("\n\nOperación cancelada por el usuario.")
        sys.exit(130)
    except ValueError as e:
        print(f"\nERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)




def create_parser():
    """Crear el analizador de argumentos con todos los subcomandos."""
    parser = argparse.ArgumentParser(
        prog="sorter-data",
        description="Organizador inteligente de archivos por metadatos con detección de duplicados",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  sorter-data run move --start /ruta --end ~/destino
  sorter-data run copy --start /ruta --end ~/destino
  sorter-data run move --start /ruta --end ~/destino --simulation
  sorter-data run move --start /ruta1,/ruta2,/ruta3 --end ~/destino

  sorter-data preset --create <nombre> --run <modo> --start /ruta --end ~/destino
  sorter-data preset <nombre> run
  sorter-data preset <nombre> simulation
  sorter-data preset <nombre> delete
  sorter-data preset list

  sorter-data info --start ~/ruta
  sorter-data --version
  sorter-data --help
        """
    )

    # Argumentos globales
    parser.add_argument(
        "--version",
        action="store_true",
        help="Mostrar información de versión"
    )

    # Analizador principal de subcomandos
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    # Comando run
    run_parser = subparsers.add_parser(
        "run",
        help="Ejecutar el organizador de archivos en modo mover o copiar"
    )
    run_parser.add_argument(
        "mode",
        choices=["move", "copy"],
        help="Modo de operación: move (por defecto) o copy"
    )
    run_parser.add_argument(
        "--start", "-s",
        required=True,
        help="Ruta(s) de origen a organizar (separadas por comas para múltiples rutas)"
    )
    run_parser.add_argument(
        "--end", "-e",
        required=True,
        help="Ruta base de destino"
    )
    run_parser.add_argument(
        "--simulation", action="store_true",
        help="Ejecutar en modo simulación (no mueve archivos)"
    )
    run_parser.set_defaults(func=cmd_run)

    # Comando preset
    preset_parser = subparsers.add_parser(
        "preset",
        help="Gestionar presets (create/list/run/delete)"
    )
    preset_parser.add_argument(
        "--create",
        help="Crear un nuevo preset con el nombre dado"
    )
    preset_parser.add_argument(
        "--run",
        choices=["move", "copy"],
        help="Modo de ejecución para el preset"
    )
    preset_parser.add_argument(
        "--start",
        help="Ruta de origen para el preset"
    )
    preset_parser.add_argument(
        "--end",
        help="Ruta de destino para el preset"
    )
    preset_parser.add_argument(
        "preset_name",
        nargs="?",
        help="Nombre del preset para operaciones list/run/delete"
    )
    preset_parser.add_argument(
        "preset_action",
        nargs="?",
        choices=["run", "simulation", "delete", "list"],
        help="Acción a realizar en el preset"
    )
    preset_parser.set_defaults(func=cmd_preset)

    # Comando info
    info_parser = subparsers.add_parser(
        "info",
        help="Analizar directorio de origen y mostrar información de archivos"
    )
    info_parser.add_argument(
        "--start", "-s",
        required=True,
        help="Ruta(s) de origen a analizar (separadas por comas para múltiples rutas)"
    )
    info_parser.set_defaults(func=cmd_info)

    return parser


def main():
    """Función principal del CLI."""
    parser = create_parser()
    args = parser.parse_args()

    # Manejar bandera --version
    if args.version:
        from sorter import __version__
        print(f"sorter versión {__version__}")
        sys.exit(0)

    # Manejar sin comando
    if args.command is None:
        parser.print_help()
        sys.exit(0)

    # Ejecutar comando
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
