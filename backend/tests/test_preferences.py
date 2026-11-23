"""Buyer preference rules (no database needed)."""

import pytest
from pydantic import ValidationError

from app.models import FoodCategory
from app.schemas.preferences import Preferences


def test_empty_preferences_are_allowed():
    prefs = Preferences()
    assert prefs.favourite_categories == [] and prefs.max_price is None


def test_repeated_categories_are_dropped_in_order():
    prefs = Preferences(favourite_categories=["cakes", "bread", "cakes"])
    assert prefs.favourite_categories == [FoodCategory.cakes, FoodCategory.bread]


def test_price_range_must_be_in_order():
    with pytest.raises(ValidationError):
        Preferences(min_price=100, max_price=50)


def test_unknown_category_is_rejected():
    with pytest.raises(ValidationError):
        Preferences(favourite_categories=["pizza"])


def test_json_uses_camel_case():
    prefs = Preferences.model_validate({"favouriteCategories": ["bread"], "maxPrice": "80"})
    assert prefs.model_dump(mode="json", by_alias=True) == {
        "favouriteCategories": ["bread"],
        "minPrice": None,
        "maxPrice": "80",
        "deliveryOnly": False,
    }
