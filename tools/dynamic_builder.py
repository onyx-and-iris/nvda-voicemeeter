#!/usr/bin/env python3
"""
Dynamic build system for nvda-voicemeeter.

This script generates PyInstaller spec files on-the-fly and builds executables
without storing intermediate files in the repository.

Usage:
    python tools/dynamic_builder.py                 # Build all kinds
    python tools/dynamic_builder.py basic           # Build basic only
    python tools/dynamic_builder.py basic banana    # Build specific kinds
    python tools/dynamic_builder.py all             # Build all kinds (explicit)

Requirements:
- PDM environment with PyInstaller installed
- controllerClient DLL files in controllerClient/{x64,x86}/
- nvda_voicemeeter package installed in environment

Environment Variables:
- PDM_BIN: Path to PDM executable (default: 'pdm')

Exit Codes:
- 0: All builds successful
- 1: One or more builds failed
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict

# Build configuration
KINDS = ['basic', 'banana', 'potato']

# Templates
PYTHON_TEMPLATE = """import voicemeeterlib

import nvda_voicemeeter

KIND_ID = '{kind}'

with voicemeeterlib.api(KIND_ID) as vm:
    with nvda_voicemeeter.draw(KIND_ID, vm) as window:
        window.run()
"""

SPEC_TEMPLATE = """# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

added_files = [
        ( '{controller_x64_path}', 'controllerClient/x64' ),
        ( '{controller_x86_path}', 'controllerClient/x86' ),
        ]

a = Analysis(
    ['{script_path}'],
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


class DynamicBuilder:
    def __init__(self, base_dir: Path, dist_dir: Path):
        self.base_dir = base_dir
        self.dist_dir = dist_dir
        self.temp_dir = None

    def validate_environment(self) -> bool:
        """Validate that all required files and dependencies are present."""

        # Check for controller client DLLs
        x64_dll = self.base_dir / 'controllerClient' / 'x64' / 'nvdaControllerClient.dll'
        x86_dll = self.base_dir / 'controllerClient' / 'x86' / 'nvdaControllerClient.dll'

        if not x64_dll.exists():
            print(f'[ERROR] Missing x64 controller client: {x64_dll}')
            return False

        if not x86_dll.exists():
            print(f'[ERROR] Missing x86 controller client: {x86_dll}')
            return False

        print('[OK] Controller client DLLs found')

        # Check PyInstaller availability
        try:
            result = subprocess.run(['pdm', 'list'], capture_output=True, text=True)
            if 'pyinstaller' not in result.stdout.lower():
                print('[ERROR] PyInstaller not found in PDM environment')
                return False
            print('[OK] PyInstaller available')
        except subprocess.CalledProcessError:
            print('[ERROR] Failed to check PDM environment')
            return False

        return True

    def __enter__(self):
        # Validate environment first
        if not self.validate_environment():
            print('[ERROR] Environment validation failed!')
            sys.exit(1)

        self.temp_dir = Path(tempfile.mkdtemp(prefix='nvda_voicemeeter_build_'))
        print(f'Using temp directory: {self.temp_dir}')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            print(f'Cleaned up temp directory: {self.temp_dir}')

    def create_python_file(self, kind: str) -> Path:
        """Create a temporary Python launcher file."""
        content = PYTHON_TEMPLATE.format(kind=kind)

        py_file = self.temp_dir / f'{kind}.py'
        with open(py_file, 'w') as f:
            f.write(content)

        return py_file

    def create_spec_file(self, kind: str, py_file: Path) -> Path:
        """Create a temporary PyInstaller spec file."""
        controller_x64_path = (self.base_dir / 'controllerClient' / 'x64').as_posix()
        controller_x86_path = (self.base_dir / 'controllerClient' / 'x86').as_posix()

        content = SPEC_TEMPLATE.format(
            script_path=py_file.as_posix(),
            controller_x64_path=controller_x64_path,
            controller_x86_path=controller_x86_path,
            kind=kind,
        )

        spec_file = self.temp_dir / f'{kind}.spec'
        with open(spec_file, 'w') as f:
            f.write(content)

        return spec_file

    def build_variant(self, kind: str) -> bool:
        """Build a single kind variant."""
        print(f'Building {kind}...')

        # Validate kind
        if kind not in KINDS:
            print(f'[ERROR] Unknown kind: {kind}. Valid kinds: {", ".join(KINDS)}')
            return False

        # Create temporary files
        py_file = self.create_python_file(kind)
        spec_file = self.create_spec_file(kind, py_file)

        # Build with PyInstaller
        dist_path = self.dist_dir / kind
        pdm_bin = os.getenv('PDM_BIN', 'pdm')
        cmd = [
            pdm_bin,
            'run',
            'pyinstaller',
            '--noconfirm',
            '--distpath',
            str(dist_path.parent),
            str(spec_file),
        ]

        try:
            result = subprocess.run(cmd, cwd=self.base_dir, capture_output=True, text=True)
            if result.returncode == 0:
                # Verify the executable was created
                exe_path = dist_path / f'{kind}.exe'
                if exe_path.exists():
                    print(f'[OK] Built {kind} -> {exe_path}')
                    return True
                else:
                    print(f'[FAIL] {kind} executable not found at {exe_path}')
                    return False
            else:
                print(f'[FAIL] Failed to build {kind}')
                if result.stderr:
                    print(f'Error: {result.stderr}')
                if result.stdout:
                    print(f'Output: {result.stdout}')
                return False
        except Exception as e:
            print(f'[ERROR] Exception building {kind}: {e}')
            return False

    def build_all_kinds(self) -> Dict[str, bool]:
        """Build all kind variants."""
        results = {}

        for kind in KINDS:
            success = self.build_variant(kind)
            results[kind] = success

        return results


def main():
    parser = argparse.ArgumentParser(description='Dynamic build system for nvda-voicemeeter')
    parser.add_argument(
        'kinds',
        nargs='*',
        choices=KINDS + ['all'],
        help='Kinds to build (default: all)',
    )
    parser.add_argument(
        '--dist-dir',
        type=Path,
        default=Path('dist'),
        help='Distribution output directory',
    )

    args = parser.parse_args()

    if not args.kinds or 'all' in args.kinds:
        kinds_to_build = KINDS
    else:
        kinds_to_build = args.kinds

    base_dir = Path.cwd()
    args.dist_dir.mkdir(exist_ok=True)

    print(f'Building kinds: {", ".join(kinds_to_build)}')

    all_results = {}

    with DynamicBuilder(base_dir, args.dist_dir) as builder:
        if 'all' in kinds_to_build or len(kinds_to_build) == len(KINDS):
            # Build all kinds
            results = builder.build_all_kinds()
            all_results.update(results)
        else:
            # Build specific kinds
            for kind in kinds_to_build:
                success = builder.build_variant(kind)
                all_results[kind] = success

    # Report results
    print('\n' + '=' * 50)
    print('BUILD SUMMARY')
    print('=' * 50)

    success_count = 0
    total_count = 0

    for build_name, success in all_results.items():
        status = '[OK]' if success else '[FAIL]'
        print(f'{status} {build_name}')
        if success:
            success_count += 1
        total_count += 1

    print(f'\nSuccess: {success_count}/{total_count}')

    if success_count == total_count:
        print('All builds completed successfully!')
        sys.exit(0)
    else:
        print('Some builds failed!')
        sys.exit(1)


if __name__ == '__main__':
    main()
