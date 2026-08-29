from enum import Enum


class AppEnv(str, Enum):
    local = "local"
    test = "test"
    prod = "prod"

    @classmethod
    def demo_allowed(cls) -> frozenset["AppEnv"]:
        """
        Окружения, в которых разрешены demo-endpoint-ы
        (demo webhook Bank131, любые будущие demo-ручки).

        Whitelist-подход: новый AppEnv (staging, qa, etc.) по умолчанию
        НЕ получает доступ к demo-эндпоинтам. Разработчик, добавляющий
        новое окружение, должен явно принять решение о включении его сюда.

        prod сюда НЕ входит никогда.
        """
        return frozenset({cls.local, cls.test})
