from src.domain.errors.does_not_exists import CustomDoesNotExist
from src.domain.ports.error.base import ApplicationError


# Единственное место, где доменные ошибки связываются с HTTP.
# Domain слой про HTTP не знает.
#
# Запись: ErrorClass -> (http_status, error_code).
# error_code — стабильная строка, является частью API contract,
# не менять без согласования.
#
# Поиск маппингов наследников учитывает MRO: для конкретной ошибки берётся
# первая найденная запись, начиная от самого ErrorClass и вверх по родителям.
ERROR_HTTP_MAP: dict[type[ApplicationError], tuple[int, str]] = {
    # auth
    # generic 404 (CustomDoesNotExist)
    CustomDoesNotExist: (404, "not_found"),
}


# Дефолт для подклассов ApplicationError, не попавших в карту явно.
# Любой такой случай — недоразумение: значит мы добавили новую ошибку,
# но забыли её смаппить. Handler логирует это на WARNING.
DEFAULT_APPLICATION_ERROR_HTTP: tuple[int, str] = (400, "application_error")


def resolve(error: ApplicationError) -> tuple[int, str]:
    """
    Найти (http_status, error_code) для исключения.

    Идём по MRO: если у конкретного класса записи нет, возьмём от родителя.
    Это позволяет иметь маппинг на уровне базы (например, AdminAuthError)
    и не дублировать его для подклассов.
    """
    for cls in type(error).__mro__:
        if cls in ERROR_HTTP_MAP:
            return ERROR_HTTP_MAP[cls]
    return DEFAULT_APPLICATION_ERROR_HTTP
