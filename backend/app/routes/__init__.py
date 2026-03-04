# Routes Package
from .diagrams import router as diagrams_router
from .code import router as code_router
from .download import router as download_router
from .utility import router as utility_router
from .auth import router as auth_router

__all__ = [
    "diagrams_router",
    "code_router",
    "download_router",
]
