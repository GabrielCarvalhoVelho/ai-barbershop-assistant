class BusinessError(Exception):
    """Erro de regra de negócio na camada de serviço."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
