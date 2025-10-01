from django.db import models
from cms.models.fields import PlaceholderRelationField, PlaceholderField
from cms.utils.placeholder import get_placeholder_from_slot
from functools import cached_property


class MyModel(models.Model):
    # your fields
    placeholders = PlaceholderRelationField()

    @cached_property
    def my_placeholder(self):
        return get_placeholder_from_slot(self.placeholders, "slot_name")

    # your methods
