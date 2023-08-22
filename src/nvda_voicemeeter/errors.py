class NVDAVMError(Exception):
    """Base NVDAVM error class"""


class NVDAVMCAPIError(NVDAVMError):
    """Exception raised when the NVDA C-API returns an error code"""

    def __init__(self, fn_name, code):
        self.fn_name = fn_name
        self.code = code
        super().__init__(f"{self.fn_name} returned {self.code}")
