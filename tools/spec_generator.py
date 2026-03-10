#!/usr/bin/env python3
"""
PyInstaller spec file generator for nvda-voicemeeter project.

This script generates .spec files for different Voicemeeter kinds (basic, banana, potato).
Based on the existing spec file patterns in the spec/ directory.

Usage:
    python tools/spec_generator.py [kind]

Arguments:
    kind: The Voicemeeter kind to generate spec for (basic, banana, potato).
          If not provided, generates all spec files.

Examples:
    python tools/spec_generator.py basic
    python tools/spec_generator.py
"""

import argparse
from pathlib import Path
from typing import List


class SpecGenerator:
    """Generate PyInstaller spec files for nvda-voicemeeter project."""

    # Supported Voicemeeter kinds
    KINDS = ['basic', 'banana', 'potato']

    def __init__(self, project_root: Path = None):
        """Initialize the spec generator.

        Args:
            project_root: Path to the project root. If None, uses current directory.
        """
        if project_root is None:
            # Assume we're running from tools/ directory
            project_root = Path(__file__).parent.parent

        self.project_root = Path(project_root)
        self.spec_dir = self.project_root / 'spec'

        # Ensure spec directory exists
        self.spec_dir.mkdir(exist_ok=True)

    def generate_spec_template(self, kind: str) -> str:
        """Generate a PyInstaller spec file template for the given kind.

        Args:
            kind: The Voicemeeter kind (basic, banana, potato).

        Returns:
            The generated spec file content as a string.
        """
        if kind not in self.KINDS:
            raise ValueError(f'Unsupported kind: {kind}. Supported kinds: {self.KINDS}')

        template = f"""# -*- mode: python ; coding: utf-8 -*-


block_cipher = None

added_files = [
        ( '../controllerClient/x64', 'controllerClient/x64' ),
        ( '../controllerClient/x86', 'controllerClient/x86' ),
        ]

a = Analysis(
    ['{kind}.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='{kind}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='{kind}',
)
"""
        return template

    def generate_entry_point(self, kind: str) -> str:
        """Generate a Python entry point script for the given kind.

        Args:
            kind: The Voicemeeter kind (basic, banana, potato).

        Returns:
            The generated Python script content as a string.
        """
        if kind not in self.KINDS:
            raise ValueError(f'Unsupported kind: {kind}. Supported kinds: {self.KINDS}')

        entry_point = f"""import voicemeeterlib

import nvda_voicemeeter

KIND_ID = '{kind}'

with voicemeeterlib.api(KIND_ID) as vm:
    with nvda_voicemeeter.draw(KIND_ID, vm) as window:
        window.run()
"""
        return entry_point

    def write_spec_file(self, kind: str, overwrite: bool = False) -> Path:
        """Write a spec file for the given kind.

        Args:
            kind: The Voicemeeter kind (basic, banana, potato).
            overwrite: Whether to overwrite existing files.

        Returns:
            Path to the created spec file.

        Raises:
            FileExistsError: If file exists and overwrite is False.
        """
        spec_file = self.spec_dir / f'{kind}.spec'
        entry_file = self.spec_dir / f'{kind}.py'

        if spec_file.exists() and not overwrite:
            raise FileExistsError(f'Spec file already exists: {spec_file}')

        if entry_file.exists() and not overwrite:
            raise FileExistsError(f'Entry point file already exists: {entry_file}')

        # Write spec file
        spec_content = self.generate_spec_template(kind)
        spec_file.write_text(spec_content, encoding='utf-8')
        print(f'Generated spec file: {spec_file}')

        # Write entry point script
        entry_content = self.generate_entry_point(kind)
        entry_file.write_text(entry_content, encoding='utf-8')
        print(f'Generated entry point: {entry_file}')

        return spec_file

    def generate_all_specs(self, overwrite: bool = False) -> List[Path]:
        """Generate spec files for all supported kinds.

        Args:
            overwrite: Whether to overwrite existing files.

        Returns:
            List of paths to the created spec files.
        """
        spec_files = []
        for kind in self.KINDS:
            try:
                spec_file = self.write_spec_file(kind, overwrite=overwrite)
                spec_files.append(spec_file)
            except FileExistsError as e:
                print(f'Skipped {kind}: {e}')
                continue

        return spec_files

    def list_existing_specs(self) -> List[str]:
        """List existing spec files in the spec directory.

        Returns:
            List of existing spec file kinds.
        """
        existing = []
        for kind in self.KINDS:
            spec_file = self.spec_dir / f'{kind}.spec'
            if spec_file.exists():
                existing.append(kind)

        return existing


def main():
    """Main entry point for the spec generator."""
    parser = argparse.ArgumentParser(
        description='Generate PyInstaller spec files for nvda-voicemeeter project',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/spec_generator.py basic    # Generate basic.spec
  python tools/spec_generator.py          # Generate all spec files
  python tools/spec_generator.py --list   # List existing spec files
  python tools/spec_generator.py --force  # Overwrite existing files
        """,
    )

    parser.add_argument(
        'kind',
        nargs='?',
        choices=SpecGenerator.KINDS,
        help=f'Voicemeeter kind to generate spec for ({", ".join(SpecGenerator.KINDS)})',
    )

    parser.add_argument('--force', '-f', action='store_true', help='Overwrite existing spec files')

    parser.add_argument('--list', '-l', action='store_true', help='List existing spec files')

    parser.add_argument(
        '--project-root', type=Path, help='Path to project root (default: detect from script location)'
    )

    args = parser.parse_args()

    # Initialize generator
    generator = SpecGenerator(project_root=args.project_root)

    # List existing files if requested
    if args.list:
        existing = generator.list_existing_specs()
        if existing:
            print('Existing spec files:')
            for kind in existing:
                spec_file = generator.spec_dir / f'{kind}.spec'
                print(f'  {kind}: {spec_file}')
        else:
            print('No existing spec files found.')
        return

    try:
        if args.kind:
            # Generate specific kind
            generator.write_spec_file(args.kind, overwrite=args.force)
            print(f'Successfully generated spec for: {args.kind}')
        else:
            # Generate all kinds
            spec_files = generator.generate_all_specs(overwrite=args.force)
            if spec_files:
                print(f'Successfully generated {len(spec_files)} spec files.')
            else:
                print('No spec files were generated (use --force to overwrite existing files).')

    except ValueError as e:
        print(f'Error: {e}')
        return 1
    except FileExistsError as e:
        print(f'Error: {e}')
        print('Use --force to overwrite existing files.')
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
