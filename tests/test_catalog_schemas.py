import pytest
from pydantic import ValidationError

from src.application.schemas.dishes import DishUpdate
from src.application.schemas.drinks import DrinkUpdate


@pytest.mark.parametrize("schema", [DishUpdate, DrinkUpdate])
@pytest.mark.parametrize("field", ["name", "price_minor", "is_available"])
def test_required_catalog_fields_cannot_be_erased(schema, field):
    with pytest.raises(ValidationError):
        schema.model_validate({field: None})


@pytest.mark.parametrize("schema", [DishUpdate, DrinkUpdate])
def test_omitted_fields_remain_unchanged(schema):
    assert schema().model_dump(exclude_unset=True) == {}


def test_nullable_drink_volume_can_be_cleared():
    assert DrinkUpdate(volume_ml=None).model_dump(exclude_unset=True) == {
        "volume_ml": None,
    }


def test_nullable_dish_description_can_be_cleared():
    assert DishUpdate(description=None).model_dump(exclude_unset=True) == {
        "description": None,
    }
