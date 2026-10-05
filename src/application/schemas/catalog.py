from typing import Any

from pydantic import BaseModel, model_validator

from src.application.messages import NULL_CATALOG_FIELD

NON_NULL_CATALOG_FIELDS = ("name", "price_minor", "is_available")


class CatalogUpdate(BaseModel):

    @model_validator(mode="before")
    @classmethod
    def reject_null_required_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for field in NON_NULL_CATALOG_FIELDS:
                if field in data and data[field] is None:
                    raise ValueError(NULL_CATALOG_FIELD.format(field=field))
        return data
