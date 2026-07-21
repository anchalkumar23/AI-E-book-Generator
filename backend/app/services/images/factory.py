from .base import ImageProvider
from .huggingface import HuggingFaceProvider
from .placeholder import PlaceholderProvider
from .pollinations import PollinationsProvider


def get_images(name: str = "huggingface", **kwargs) -> ImageProvider:
    """Adding a provider = one import + one line here."""
    if name == "huggingface":
        return HuggingFaceProvider(**kwargs)
    if name == "pollinations":
        return PollinationsProvider()
    if name == "placeholder":
        return PlaceholderProvider()
    raise ValueError(f"unknown image provider: {name}")
