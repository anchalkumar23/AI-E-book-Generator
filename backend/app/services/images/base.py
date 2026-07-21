from abc import ABC, abstractmethod

REAL_PERSON_MESSAGE = (
    "Real person image required. "
    "Please provide a licensed image or add it manually."
)


class ImageProvider(ABC):
    """Returns a served URL for the page image, or None if none was produced."""

    @abstractmethod
    def generate(self, prompt: str, book_id: int, page: int) -> str | None:
        ...
