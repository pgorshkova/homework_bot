class APIErrException(Exception):
    """Класс исключений для обработки Practicum.Homeworks API."""
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message