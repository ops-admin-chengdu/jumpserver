# -*- coding: utf-8 -*-
#
import json

from django.db import models
from django import forms
from django.utils import six
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _
from rest_framework import serializers
from .utils import get_signer

signer = get_signer()


class DictField(forms.Field):
    widget = forms.Textarea

    def to_python(self, value):
        """Returns a Python boolean object."""
        # Explicitly check for the string 'False', which is what a hidden field
        # will submit for False. Also check for '0', since this is what
        # RadioSelect will provide. Because bool("True") == bool('1') == True,
        # we don't need to handle that explicitly.
        if isinstance(value, six.string_types):
            try:
                value = json.loads(value)
                return value
            except json.JSONDecodeError:
                return ValidationError(_("Not a valid json"))
        else:
            return ValidationError(_("Not a string type"))

    def validate(self, value):
        if isinstance(value, ValidationError):
            raise value
        if not value and self.required:
            raise ValidationError(self.error_messages['required'], code='required')

    def has_changed(self, initial, data):
        # Sometimes data or initial may be a string equivalent of a boolean
        # so we should run it through to_python first to get a boolean value
        return self.to_python(initial) != self.to_python(data)


class StringIDField(serializers.Field):
    def to_representation(self, value):
        return {"pk": value.pk, "name": value.__str__()}


class StringManyToManyField(serializers.RelatedField):
    def to_representation(self, value):
        return value.__str__()


class EncryptMixin:
    def from_db_value(self, value, expression, connection, context):
        if value is not None:
            return signer.unsign(value)
        return super().from_db_value(self, value, expression, connection, context)

    def get_prep_value(self, value):
        if value is None:
            return value
        return signer.sign(value).decode('utf-8')


class EncryptTextField(EncryptMixin, models.TextField):
    description = _("Encrypt field using Secret Key")


class EncryptCharField(EncryptMixin, models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 2048
        super().__init__(*args, **kwargs)

