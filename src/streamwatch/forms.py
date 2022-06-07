from django import forms
#from .models import LeafPack, LeafPackType, Macroinvertebrate, LeafPackBug, LeafPackSensitivityGroup
from dataloaderinterface.models import SiteRegistration
from django.core.exceptions import ObjectDoesNotExist
from leafpack.models import LeafPackType

class MDLCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    template_name = 'mdl-checkbox-select-multiple.html'

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        context['choices'] = [choice[1][0] for choice in context['widget']['optgroups']]
        context['name'] = name
        return self._render(self.template_name, context, renderer)

class StreamWatchForm(forms.Form):
    
    ACTIVITY_TYPE_CHOICES = (('chemical', 'Chemical'), ('biological', 'biological'), ('baterial', 'baterial'))
    ACTIVITY_TYPE_CHOICES_LIST = ['chemical', 'biological', 'baterial']

    def __init__(self, *args, **kwargs):
        super(StreamWatchForm, self).__init__(*args, **kwargs)
        #self.fields['types'].initial = self.ACTIVITY_TYPE_CHOICES_LIST
    
    invesgator1 = forms.DateField(
        label='Invesgator #1'
    )       
    invesgator2 = forms.DateField(
        label='Invesgator #2'
    )   
    collect_date = forms.DateField(
        label='Date'
    )
    collect_time = forms.TimeField(
        label='Time'
    )
    
    types = forms.ModelMultipleChoiceField(
        widget=MDLCheckboxSelectMultiple,
        label='Activity type(s):',
        required=True,
        queryset=LeafPackType.objects.filter(created_by=None),
    )