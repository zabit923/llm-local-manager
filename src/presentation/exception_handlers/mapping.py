from src.domain.errors.does_not_exists import CustomDoesNotExist
from src.domain.ports.error.base import ApplicationError
from src.presentation.exception_handlers import constants


ERROR_HTTP_MAP: dict[type[ApplicationError], tuple[int, str]] = {
    CustomDoesNotExist: (404, constants.NOT_FOUND),
}


DEFAULT_APPLICATION_ERROR_HTTP = (400, constants.APPLICATION_ERROR)


def resolve(error: ApplicationError) -> tuple[int, str]:
    for cls in type(error).__mro__:
        if cls in ERROR_HTTP_MAP:
            return ERROR_HTTP_MAP[cls]
    return DEFAULT_APPLICATION_ERROR_HTTP
