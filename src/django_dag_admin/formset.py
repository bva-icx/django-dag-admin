# -*- coding: utf-8 -*-
from django.forms.models import BaseInlineFormSet

class DjangoDagAdminFormSet(BaseInlineFormSet):
    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs['parent_object'] = self.instance
        return kwargs
