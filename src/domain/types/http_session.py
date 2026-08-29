# Разведение по типам для DI: своя session, изолированная от Bank131.
# NewType — zero-cost, runtime это тот же ClientSession.
from typing import NewType

from aiohttp import ClientSession


MerchantWebhookHttpSession = NewType("MerchantWebhookHttpSession", ClientSession)
