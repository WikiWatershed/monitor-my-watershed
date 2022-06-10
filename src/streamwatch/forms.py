from django import forms
#from .models import LeafPack, LeafPackType, Macroinvertebrate, LeafPackBug, LeafPackSensitivityGroup
from dataloaderinterface.models import SiteRegistration
from django.core.exceptions import ObjectDoesNotExist
from leafpack.models import LeafPackType
from .models import variable_choice_options

place_holder_choices = (
        (1, 'Choice #1'), 
        (2, 'Choice #2'),
        (3, 'Choice #3')
    )
class MDLCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    template_name = 'mdl-checkbox-select-multiple.html'

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        context['choices'] = [choice[1][0] for choice in context['widget']['optgroups']]
        context['name'] = name
        return self._render(self.template_name, context, renderer)

class StreamWatchForm(forms.Form):
    
    ACTIVITY_TYPE_CHOICES = (('chemical', 'Chemical Action Team'), ('biological', 'Biological Action Team'), ('baterial', 'Baterial Action Team'))

    def __init__(self, *args, **kwargs):
        super(StreamWatchForm, self).__init__(*args, **kwargs)
        #self.fields['types'].initial = self.ACTIVITY_TYPE_CHOICES_LIST
    
    investigator1 = forms.CharField(
        required=False,
        label='Investigator #1'
    )       
    investigator2 = forms.CharField(
        required=False,
        label='Investigator #2'
    )   
    collect_date = forms.DateField(
        required=False,
        label='Date'
    )
    collect_time = forms.TimeField(
        required=False,
        label='Time'
    )
    project_name = forms.ChoiceField(
        required=False,
        widget=forms.Select,
        label='Project Name',
        choices= place_holder_choices,
        initial='1'
    )
    reach_length = forms.FloatField(
        label='Approximate Reach Length',
        required=False,
    )
    # mutiple choices
    activity_type = forms.MultipleChoiceField(
        widget=MDLCheckboxSelectMultiple,
        label='Activity type(s)',
        required=True,
        choices = ACTIVITY_TYPE_CHOICES)    

    
class StreamWatchForm2(forms.Form):
    weather_condition_choices = (
        (1, 'Clear'),
        (2, 'Partly cloudy'),
        (3, 'Overcast')
    )
    water_color_choices = ((1,'Clear'),
        (2,'Green'),
        (3,'Blue-green'),
        (4,'Brown'),
        (5,'Yellow'),
        (6,'Gray'),
        (7,'Other'))

    water_odor_choices = (
        (1,'Normal'),
        (2,'Anaerobic'),
        (3,'Sulfuric'),
        (4,'Sewage'),
        (5,'Petroleum'),
        (6,'Other'))

    abundance_choices = variable_choice_options('wildlife')
    # types = forms.ModelMultipleChoiceField(
    #     widget=MDLCheckboxSelectMultiple,
    #     label='Activity type(s):',
    #     required=True,
    #     queryset=LeafPackType.objects.filter(created_by=None),
    # )

    #Wildlife Observations
    # wildlife_obs = forms.ModelMultipleChoiceField(
    #     widget=MDLCheckboxSelectMultiple,
    #     required=True,
    #     label='Wildlife Observations:',
    #     queryset= abundance_choices,
    # )
    
    # Visual Assessment (All Forms)
    weather_cond = forms.MultipleChoiceField(
        widget=MDLCheckboxSelectMultiple,
        required=False,
        label='Current Weather Conditions',
        choices= water_odor_choices,
    )
    time_since_last_precip = forms.ChoiceField(
        required=False,
        widget=forms.Select,
        label='Time Since Last Rain or Snowmelt',
        choices= place_holder_choices,
        initial='1'
    )    
    water_color = forms.ChoiceField(
        required=False,
        widget=forms.Select,
        label='Water Color',
        choices= water_color_choices,
        initial='1'
    )
    water_odor = forms.MultipleChoiceField(
        widget=MDLCheckboxSelectMultiple,
        required=False,
        label='Water Odor',
        choices= water_odor_choices,
    )
    turbidity = forms.ChoiceField(
        required=False,
        widget=forms.Select,
        label='Turbidity',
        choices= place_holder_choices,
        initial='1'
    )
    water_movement = forms.ChoiceField(
        required=False,
        widget=forms.Select,
        label='Water Movement',
        choices= place_holder_choices,
        initial='1'
    )
    aquatic_veg_amount = forms.ChoiceField(
        required=True,
        widget=forms.Select,
        label='Aquatic Vegetation Amount',
        choices= place_holder_choices,
        initial='1'
    )
    aquatic_veg_type = forms.MultipleChoiceField(
        widget=MDLCheckboxSelectMultiple,
        required=True,
        label='Aquatic Vegetation Type',
        choices= place_holder_choices,
    )
    surface_coating = forms.MultipleChoiceField(
        widget=MDLCheckboxSelectMultiple,
        required=True,
        label='Surface Coating',
        choices= place_holder_choices,
    )
    algae_amount = forms.ChoiceField(
        required=True,
        widget=forms.Select,
        label='Algae Amount',
        choices= place_holder_choices,
        initial='1'
    )
    algae_type = forms.MultipleChoiceField(
        widget=MDLCheckboxSelectMultiple,
        required=True,
        label='Algae Type',
        choices= place_holder_choices,
    )
    site_observation = forms.CharField(
        required=False,
        label='General Comments and Site Observations',
        max_length=255
    )   
    
    
  # In-stream Habitat Assessment (BAT form)  
    
    
    

    
    
class StreamWatchForm3(forms.Form):
    
    air_temp = forms.FloatField(
        label='Air Temperature',
        required=False,
    )