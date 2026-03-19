import ctypes as ct
import platform
from pathlib import Path

from .errors import NVDAVMError

try:
    import winreg
except ImportError as e:
    ERR_MSG = 'winreg module not found, only Windows OS supported'
    raise NVDAVMError(ERR_MSG) from e

# Defense against edge cases where winreg imports but we're not on Windows
if platform.system() != 'Windows':
    raise NVDAVMError('Only Windows OS supported')

BITS = 64 if ct.sizeof(ct.c_void_p) == 8 else 32

REG_KEY = '\\'.join(
    filter(
        None,
        (
            'SOFTWARE',
            'WOW6432Node' if BITS == 64 else '',
            'Microsoft',
            'Windows',
            'CurrentVersion',
            'Uninstall',
            'NVDA',
        ),
    )
)


def get_nvdapath():
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'{}'.format(REG_KEY)) as nvda_key:
        return winreg.QueryValueEx(nvda_key, r'UninstallDirectory')[0]


try:
    NVDA_PATH = Path(get_nvdapath()) / 'nvda.exe'
except FileNotFoundError:
    NVDA_PATH = ''


controller_path = Path(__file__).parents[2].resolve() / 'controllerClient'
if not controller_path.exists():
    controller_path = Path('_internal') / 'controllerClient'

DLL_PATH = controller_path / f'x{64 if BITS == 64 else 86}' / 'nvdaControllerClient.dll'

libc = ct.WinDLL(str(DLL_PATH))
