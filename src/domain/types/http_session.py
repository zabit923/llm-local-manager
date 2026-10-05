from typing import NewType

from aiohttp import ClientSession

MerchantWebhookHttpSession = NewType(
    "MerchantWebhookHttpSession", ClientSession
)
