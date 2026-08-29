import logging
import sys

from src.domain.configs.app_env import AppEnv


class HealthcheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/healthcheck" not in record.getMessage()


def setup_logging(app_env: AppEnv) -> None:
    """
    Единая настройка логирования для всего приложения.

    test/local: DEBUG для наших модулей — видим Bank131 requests,
                ProcessPayoutUseCase шаги, outbox события.
    prod: WARNING — только ошибки и критические события.
    """
    # is_debug = app_env in AppEnv.demo_allowed()
    is_debug = True

    root_level = logging.WARNING
    app_level = logging.DEBUG if is_debug else logging.WARNING

    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    formatter = logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)

    # Root logger — WARNING чтобы не шумели сторонние библиотеки
    root = logging.getLogger()
    root.setLevel(root_level)
    root.addHandler(handler)

    # Наши модули
    for name in (
        "src.application",
        "src.infrastructure",
        "src.presentation",
        "src.entrypoint",
        "src.domain",
    ):
        logging.getLogger(name).setLevel(app_level)

    # Убрать healthcheck из uvicorn access
    logging.getLogger("uvicorn.access").addFilter(HealthcheckFilter())

    if is_debug:
        logging.getLogger("src").setLevel(logging.DEBUG)
        logging.getLogger(__name__).info(
            "Logging: DEBUG mode (APP_ENV=%s)", app_env.value
        )
