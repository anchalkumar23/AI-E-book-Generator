from .base import ImageProvider


class PlaceholderProvider(ImageProvider):
    """Phase 1 default: prompts are generated and stored, but no image is rendered.

    FLUX.1 Schnell / Z Image Turbo will slot in here as a sibling class.
    """

    def generate(self, prompt: str, book_id: int, page: int) -> str | None:
        return None
