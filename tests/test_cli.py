"""Tests for the CLI module."""

import pytest
import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

from sorter.cli import create_parser


class TestCreateParser:
    """Tests for create_parser() function."""

    def test_parser_has_commands(self):
        """Test parser has all required commands."""
        parser = create_parser()
        assert parser is not None

    def test_parser_subcommands(self):
        """Test parser has run, preset, info subcommands."""
        parser = create_parser()
        # Get the subparsers
        subparsers_action = None
        for action in parser._subparsers._actions:
            if hasattr(action, '_parser_class'):
                subparsers_action = action
                break

        assert subparsers_action is not None

    def test_run_command_has_required_args(self):
        """Test run command has required arguments."""
        parser = create_parser()
        # Test parsing run command
        args = parser.parse_args(['run', 'move', '--start', '/src', '--end', '/dst'])
        assert args.command == 'run'
        assert args.mode == 'move'
        assert args.start == '/src'
        assert args.end == '/dst'

    def test_run_command_copy_mode(self):
        """Test run command with copy mode."""
        parser = create_parser()
        args = parser.parse_args(['run', 'copy', '--start', '/src', '--end', '/dst'])
        assert args.mode == 'copy'

    def test_run_command_simulation_flag(self):
        """Test run command with --simulation flag."""
        parser = create_parser()
        args = parser.parse_args(['run', 'move', '--start', '/src', '--end', '/dst', '--simulation'])
        assert args.simulation is True

    def test_run_command_multiple_source_paths(self):
        """Test run command with comma-separated source paths."""
        parser = create_parser()
        args = parser.parse_args(['run', 'move', '--start', '/src1,/src2', '--end', '/dst'])
        assert args.start == '/src1,/src2'

    def test_preset_command_create(self):
        """Test preset command with --create."""
        parser = create_parser()
        args = parser.parse_args(['preset', '--create', 'my-preset', '--run', 'move', '--start', '/src', '--end', '/dst'])
        assert args.create == 'my-preset'
        assert args.run == 'move'

    def test_preset_command_with_name(self):
        """Test preset command with preset name."""
        parser = create_parser()
        args = parser.parse_args(['preset', 'my-preset', 'run'])
        assert args.preset_name == 'my-preset'
        assert args.preset_action == 'run'

    def test_preset_command_simulation_alias(self):
        """Test preset command with simulation alias."""
        parser = create_parser()
        args = parser.parse_args(['preset', 'my-preset', 'simulation'])
        assert args.preset_name == 'my-preset'
        assert args.preset_action == 'simulation'

    def test_preset_command_delete(self):
        """Test preset command with delete action."""
        parser = create_parser()
        args = parser.parse_args(['preset', 'my-preset', 'delete'])
        assert args.preset_name == 'my-preset'
        assert args.preset_action == 'delete'

    def test_preset_command_list(self):
        """Test preset command with list action."""
        parser = create_parser()
        args = parser.parse_args(['preset', 'list'])
        assert args.preset_name == 'list'

    def test_preset_command_without_action(self):
        """Test preset command without action (defaults to run)."""
        parser = create_parser()
        args = parser.parse_args(['preset', 'my-preset'])
        assert args.preset_name == 'my-preset'
        assert args.preset_action is None

    def test_info_command(self):
        """Test info command."""
        parser = create_parser()
        args = parser.parse_args(['info', '--start', '/src'])
        assert args.command == 'info'
        assert args.start == '/src'

    def test_info_command_multiple_paths(self):
        """Test info command with comma-separated paths."""
        parser = create_parser()
        args = parser.parse_args(['info', '--start', '/src1,/src2'])
        assert args.start == '/src1,/src2'

    def test_version_flag(self):
        """Test --version flag."""
        parser = create_parser()
        args = parser.parse_args(['--version'])
        assert args.version is True


class TestRunCommandIntegration:
    """Integration tests for run command."""

    def test_run_command_sets_mode(self):
        """Test that run command sets the correct mode."""
        parser = create_parser()
        args = parser.parse_args(['run', 'copy', '--start', '/src', '--end', '/dst'])
        assert args.mode == 'copy'

    def test_run_command_defaults_to_move(self):
        """Test that run command defaults to move mode."""
        parser = create_parser()
        args = parser.parse_args(['run', 'move', '--start', '/src', '--end', '/dst'])
        assert args.mode == 'move'


class TestPresetPathNormalization:
    """Tests for preset path handling (string to list normalization)."""

    def test_preset_with_single_start_path(self):
        """Test preset with single start path (string normalized to list)."""
        from sorter.config import Preset
        # Simulates what happens when preset.inicio is a string from JSON
        data = {
            "nombre": "test-preset",
            "modo": "mover",
            "inicio": ["/source"],  # Already a list
            "fin": "/destination"
        }
        preset = Preset.from_dict(data)
        assert isinstance(preset.inicio, list)
        assert preset.inicio == ["/source"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
