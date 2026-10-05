from dataclasses import dataclass


@dataclass(frozen=True)
class CorsRouteConfig:
    origins: tuple[str, ...]
    allow_methods: tuple[str, ...]
    allow_headers: tuple[str, ...]
