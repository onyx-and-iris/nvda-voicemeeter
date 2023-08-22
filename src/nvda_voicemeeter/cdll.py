import ctypes as ct
from pathlib import Path

bits = 64 if ct.sizeof(ct.c_voidp) == 8 else 32

controller_path = Path(__file__).parents[2].resolve() / "controllerClient"
if not controller_path.exists():
    controller_path = Path(__file__).parents[3].resolve() / "controllerClient"

DLL_PATH = controller_path / f"x{64 if bits == 64 else 86}" / f"nvdaControllerClient{bits}.dll"

libc = ct.CDLL(str(DLL_PATH))
