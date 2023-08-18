from django import forms
from django.forms import formset_factory

from typing import Dict
from typing import Any
import datetime

from dataloaderinterface.models import Affiliation
from streamwatch import models
from streamwatch import timeutils
from odm2.crud import users


def _get_user_choices() -> tuple[tuple[int, str]]:
    """Initialize the user list with affiliation and account name"""

    def format_name(a) -> str:
        name = f"{a[2]}, {a[1]}"
        if a[3] is not None:
            name += f" ({a[3]})"
        return name

    return tuple(((a[0], format_name(a)) for a in users.read_account_affiliations()))


class MDLCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    template_name = "mdl-checkbox-select-multiple.html"

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        context["choices"] = [choice[1][0] for choice in context["widget"]["optgroups"]]
        context["name"] = name
        return self._render(self.template_name, context, renderer)


class SetupForm(forms.Form):
    __USERS = _get_user_choices()
    # __USERS = [
    #    affiliation.affiliation_id
    #    for affiliation in (
    #        Affiliation.objects.filter(organization__isnull=False).filter(
    #            account_id__isnull=False
    #        )
    #    )
    # ]

    ASSESSMENT_TYPE_CHOICES = (
        ("school", "StreamWatch Schools"),
        # PRT - disabled for the time being until these forms are fully implemented
        # ('chemical', 'Chemical Action Team'),
        # ('biological', 'Biological Action Team'),
        # ('baterial', 'Baterial Action Team'),
    )

    investigator1 = forms.ChoiceField(
        choices=__USERS,
        # queryset=Affiliation.objects.filter(affiliation_id__in=(user_affiliations)).for_display(),
        required=True,
        help_text="Select a user as the main investigator",
        label="Investigator #1",
    )
    investigator2 = forms.ChoiceField(
        choices=__USERS,
        # queryset=Affiliation.objects.filter(affiliation_id__in=(user_affiliations)).for_display(),
        required=False,
        help_text="Select a user as the secondary investigator",
        label="Investigator #2",
    )
    collect_date = forms.DateField(
        required=False,
        label="Date",
        initial=datetime.datetime.now().date(),
    )
    collect_time = forms.TimeField(
        required=False,
        label="Time",
        input_formats=[
            # see for acceptable formats https://docs.djangoproject.com/en/4.0/ref/templates/builtins/#date
            "%H:%M",  # 14:30
            "%H:%M:%S",  # 14:30:59
            "%H:%M:%S.%f",  # 14:30:59.000200
            "%I:%M %p",  # 02:30p.m.
            "%I:%M%p",  # 02:30PM
        ],
        initial="00:00",
    )
    collect_tz = forms.ChoiceField(
        required=False,
        label="Timezone",
        choices=[(None, "")]
        + timeutils.make_tz_tuple_list(
            timeutils.tz_key_shortlist, datetime.datetime(2022, 1, 1)
        ),
        initial="US/Eastern",
    )

    # assessment_type = forms.MultipleChoiceField(
    #    widget=MDLCheckboxSelectMultiple,
    #    label="Assessment type(s)",
    #    required=True,
    #    choices=ASSESSMENT_TYPE_CHOICES,
    # )


# Visual Assessment (All Forms)
class VisualAssessmentForm(forms.Form):
    # Weather Current Conditions
    weather_cond = forms.TypedMultipleChoiceField(
        widget=MDLCheckboxSelectMultiple,
        required=False,
        label="Current Weather Conditions",
        coerce=int,
        choices=models.variable_choice_options("weather", False),
    )
    time_since_last_precip = forms.TypedChoiceField(
        required=False,
        widget=forms.Select,
        label="Time Since Last Rain or Snowmelt",
        coerce=int,
        choices=models.variable_choice_options("precipitation"),
        initial="1",
    )

    # Water Conditions
    water_color = forms.TypedChoiceField(
        required=False,
        widget=forms.Select,
        label="Water Color:",
        coerce=int,
        choices=models.variable_choice_options("waterColor"),
        initial="1",
    )
    water_odor = forms.TypedMultipleChoiceField(
        widget=MDLCheckboxSelectMultiple,
        required=False,
        label="Water Odor",
        coerce=int,
        choices=models.variable_choice_options("waterOdor", False),
    )
    clarity = forms.TypedChoiceField(
        required=False,
        widget=forms.Select,
        label="Clarity",
        coerce=int,
        choices=models.variable_choice_options("clarity"),
        initial="1",
    )
    water_movement = forms.TypedChoiceField(
        required=False,
        widget=forms.Select,
        label="Water Movement",
        coerce=int,
        choices=models.variable_choice_options("waterMovement"),
        initial="1",
    )
    surface_coating = forms.TypedMultipleChoiceField(
        widget=MDLCheckboxSelectMultiple,
        required=False,
        label="Surface Coating",
        coerce=int,
        choices=models.variable_choice_options("surfaceCoating", False),
    )
    aquatic_veg_amount = forms.TypedChoiceField(
        required=False,
        widget=forms.Select,
        label="Aquatic Vegetation Amount",
        coerce=int,
        choices=models.variable_choice_options("aquaticVegetation"),
        initial="1",
    )
    aquatic_veg_type = forms.TypedMultipleChoiceField(
        widget=MDLCheckboxSelectMultiple,
        required=False,
        label="Aquatic Vegetation Type",
        coerce=int,
        choices=models.variable_choice_options("aquaticVegetationType", False),
    )
    algae_amount = forms.TypedChoiceField(
        required=False,
        widget=forms.Select,
        label="Algae Amount",
        coerce=int,
        choices=models.variable_choice_options("algaeAmount"),
        initial="1",
    )
    algae_type = forms.TypedMultipleChoiceField(
        widget=MDLCheckboxSelectMultiple,
        required=False,
        label="Algae Type",
        coerce=int,
        choices=models.variable_choice_options("algaeType", False),
    )
    site_observation = forms.CharField(
        widget=forms.Textarea(),
        required=False,
        label="General Comments and Site Observations (maximum 255 characters)",
        max_length=255,
    )


class SimpleHabitatAssessmentForm(forms.Form):
    # Simple Habitat Assesment (School form)
    simple_woody_debris_amt = forms.TypedChoiceField(
        required=False,
        widget=forms.Select,
        label="Woody Debris Amount",
        coerce=int,
        choices=models.variable_choice_options("woodyDebris"),
        initial="1",
    )
    simple_woody_debris_type = forms.TypedChoiceField(
        required=False,
        widget=forms.Select,
        label="Woody Debris Type",
        coerce=int,
        choices=models.variable_choice_options("woodyDebrisType"),
        initial="1",
    )
    simple_tree_canopy = forms.TypedChoiceField(
        required=False,
        widget=forms.Select,
        label="Tree Canopy",
        coerce=int,
        choices=models.variable_choice_options("treeCanopy"),
        initial="1",
    )
    simple_land_use = forms.MultipleChoiceField(
        widget=MDLCheckboxSelectMultiple,
        required=False,
        label="Land Use Characteristics",
        choices=models.variable_choice_options("landUse", False),
    )


class StreamHabitatAssessmentForm(forms.Form):
    # Stream Habitat Assessment (BAT form)
    reach_length = forms.FloatField(
        label="Approximate Reach Length",
        required=False,
    )
    instream_structure = forms.MultipleChoiceField(
        widget=MDLCheckboxSelectMultiple,
        required=False,
        label="In-Stream Structures",
        choices=models.variable_choice_options("instreamStructures", False),
    )
    stream_flow = forms.ChoiceField(
        required=False,
        widget=forms.Select,
        label="Stream Flow",
        choices=models.variable_choice_options("streamFlow"),
        initial="1",
    )
    percent_riffle = forms.ChoiceField(
        required=False,
        widget=forms.Select,
        label="Percent Riffle Morphology",
        choices=(),
        initial="1",
    )
    percent_run = forms.ChoiceField(
        required=False,
        widget=forms.Select,
        label="Percent Run Morphology",
        choices=(),
        initial="1",
    )
    percent_pool = forms.ChoiceField(
        required=False,
        widget=forms.Select,
        label="Percent Pool Morphology",
        choices=(),
        initial="1",
    )
    woody_debris_amt = forms.ChoiceField(
        required=False,
        widget=forms.Select,
        label="Woody Debris Amount",
        choices=models.variable_choice_options("woodyDebris"),
        initial="1",
    )
    macroinvert_habitat_type = forms.MultipleChoiceField(
        widget=MDLCheckboxSelectMultiple,
        required=False,
        label="Macroinvertebrate Habitat Types",
        choices=models.variable_choice_options("macroinvertHabitat", False),
    )
    percent_silt_clay = forms.ChoiceField(
        required=False,
        widget=forms.Select,
        label="Percent Silt and Clay Substrate",
        choices=(),
        initial="1",
    )
    percent_sand = forms.ChoiceField(
        required=False,
        widget=forms.Select,
        label="Percent Sand Substrate",
        choices=(),
        initial="1",
    )
    percent_gravel = forms.ChoiceField(
        required=False,
        widget=forms.Select,
        label="Percent Gravel Substrate",
        choices=(),
        initial="1",
    )
    percent_cobble = forms.ChoiceField(
        required=False,
        widget=forms.Select,
        label="Percent Cobble Substrate",
        choices=(),
        initial="1",
    )
    percent_boulder = forms.ChoiceField(
        required=False,
        widget=forms.Select,
        label="Percent Boulder Substrate",
        choices=(),
        initial="1",
    )
    percent_bedrock = forms.ChoiceField(
        required=False,
        widget=forms.Select,
        label="Percent Bedrock Substrate",
        choices=(),
        initial="1",
    )

    # Riparian Habitat Assessment (BAT form)
    bank_veg_type = forms.MultipleChoiceField(
        widget=MDLCheckboxSelectMultiple,
        required=False,
        label="Bank Vegetation Type",
        choices=models.variable_choice_options("bankVegetation", False),
    )
    tree_canopy = forms.ChoiceField(
        required=False,
        widget=forms.Select,
        label="Tree Canopy Coverage",
        choices=models.variable_choice_options("treeCanopy"),
        initial="1",
    )
    land_use = forms.MultipleChoiceField(
        widget=MDLCheckboxSelectMultiple,
        required=False,
        label="Land Uses in 1/4 Mile Radius",
        choices=models.variable_choice_options("landuseQuarterMile", False),
    )
    litter_amt = forms.ChoiceField(
        required=False,
        widget=forms.Select,
        label="Litter Concentration",
        choices=models.variable_choice_options("litter"),
        initial="1",
    )
    wildlife_obs = forms.MultipleChoiceField(
        widget=MDLCheckboxSelectMultiple,
        required=False,
        label="Wildlife Observations",
        choices=models.variable_choice_options("wildlife", False),
    )
    macroinvert_sample_collect = forms.ChoiceField(
        required=False,
        widget=forms.Select,
        label="Macroinvertebrate Sample Collected?",
        choices=(),
        initial="1",
    )


class SimpleWaterQualityForm(forms.Form):
    PARAMETER_CHOICES = (
        ("simple_air_temperature", "Air Temperature"),
        ("simple_dissolved_oxygen", "Dissolved Oxygen"),
        ("simple_nitrate", "Nitrate Nitrogen"),
        ("simple_phosphate", "Phosphate"),
        ("simple_ph", "pH"),
        ("simple_salinity", "Salinity"),
        ("simple_turbidity", "Turbidity"),
        ("simple_turbidity_reagent_amt", "Amount of Turbidity Reagent Added"),
        ("simple_turbidity_sample_size", "Turbidity Sample Size"),
        ("simple_water_temperature", "Water Temperature"),
    )

    def __init__(self, *args, **kwargs):
        super(SimpleWaterQualityForm, self).__init__(*args, **kwargs)
        counter = 1
        for keyname, plabel in self.PARAMETER_CHOICES:
            self.fields[keyname] = forms.FloatField(label=plabel, required=False)
            counter += 1


class WaterQualityParametersForm(forms.Form):
    # TODO convert index to variable ID
    PARAMETER_CHOICES = (
        (1, "Air Temperature"),
        (2, "Dissolved Oxygen (mg/L)"),
        (3, "Nitrate"),
        (4, "Phosphate"),
        (5, "pH"),
        (6, "Specific Conductivity (uL/cm)"),
        (7, "Total Dissolved Solids"),
        (8, "Turbidity (JTU)"),
        (9, "Water Temp (C)"),
    )

    parameter = forms.ChoiceField(
        required=True,
        widget=forms.Select,
        label="Parameter",
        choices=PARAMETER_CHOICES,
        # initial='1'
    )

    measurement = forms.FloatField(
        label="Measurement",
        required=True,
    )

    unit = forms.ChoiceField(
        required=True,
        widget=forms.Select,
        label="Unit",
        choices=(),
        # initial='1'
    )


class WaterQualityParametersSet(forms.BaseFormSet):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, prefix="parameter", **kwargs)


class WaterQualityForm(forms.Form):
    meter = forms.CharField(required=False, label="pH Meter #")
    calibration_date = forms.DateField(required=False, label="Date of Last Calibration")
    test_method = forms.ChoiceField(
        required=False,
        widget=forms.Select,
        label="Test Method",
        choices=(),
        initial="1",
    )
    parameters = formset_factory(
        WaterQualityParametersForm, formset=WaterQualityParametersSet, extra=3
    )

    def clean_data(self) -> Dict[str, Any]:
        cleaned = self.cleaned_data
        parameters = {}
        for key in self.data:
            if "parameter" not in key:
                continue
            _, index, attribute = key.split("-")
            if index not in parameters:
                parameters[index] = models.CATParameter()
            setattr(parameters[index], attribute, self.data[key])
        cleaned["parameters"] = list(parameters.values())
        return cleaned


class FlowMeasurementsForm(forms.Form):
    # Velocity (BAT form)
    rep_wetted_width = forms.FloatField(
        label="Representative Wetted Width",
        required=False,
    )
    rep_depth1 = forms.FloatField(
        label="Representative Depth Profile 1",
        required=False,
    )
    rep_depth2 = forms.FloatField(
        label="Representative Depth Profile 2",
        required=False,
    )
    rep_depth3 = forms.FloatField(
        label="Representative Depth Profile 3",
        required=False,
    )
    rep_depth4 = forms.FloatField(
        label="Representative Depth Profile 4",
        required=False,
    )
    rep_depth5 = forms.FloatField(
        label="Representative Depth Profile 5",
        required=False,
    )
    avg_depth = forms.FloatField(
        label="Average Depth",
        required=False,
    )
    avg_float_time = forms.FloatField(
        label="Average Float Time",
        required=False,
    )
    avg_velocity = forms.FloatField(
        label="Average Velocity",
        required=False,
    )
    physical_assessment = forms.ChoiceField(
        required=False,
        widget=forms.Select,
        label="Physical Assessment Conducted?",
        choices=(),
        initial="1",
    )
