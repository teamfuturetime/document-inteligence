class PipelineError(Exception):
    """Safe error code for adapters. Native stderr and input contents stay private."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
