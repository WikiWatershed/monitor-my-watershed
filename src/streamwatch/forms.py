from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from django.forms import formset_factory
from django.conf import settings

import os
from typing import Any, Dict, Tuple
import datetime

from dataloaderinterface.models import Affiliation
from streamwatch import models
from streamwatch import timeutils
from odm2.crud import users

PHOTO_DIRECTORY = os.path.join(settings.MEDIA_ROOT, "streamwatch_site_photos")


def _get_user_choices() -> tuple[tuple[int, str]]:
    """Initialize the user list with affiliation and account name"""

    def format_name(a) -> str:
        first = a[1]
        last = a[2]
        name = f"{first}, {last}"
        if a[3] is not None:
            name += f" ({a[3]})"
        return name

    user_options = []
    for a in users.read_account_affiliations():
        if a[1] is None or a[1] == "" or a[2] is None or a[2] == "":
            continue
        user_options.append((a[0], format_name(a)))
    return tuple(user_options)


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
    water_odor_other = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False,
        label="Water Odor Other Description",
        max_length=255,
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
    # Tuple pattern 'field_name[str], label[str], non-detectable[bool] min[optional[float]], max[optional[float]],
    PARAMETER_CHOICES = (
        ("simple_air_temperature", "Air Temperature", False, -40, 45),
        ("simple_dissolved_oxygen", "Dissolved Oxygen", True, 0, 20),
        ("simple_nitrate", "Nitrate Nitrogen", True, 0, 40),
        ("simple_phosphate", "Phosphate", True, 0, 4),
        ("simple_ph", "pH", False, 1, 14),
        ("simple_salinity", "Salinity", True, 0, 40),
        ("simple_turbidity", "Turbidity", True, 0, 300),
        ("simple_water_temperature", "Water Temperature", False, 1, 40),
    )

    def __set_validators(
        self, limits=Tuple[None | float, None | float]
    ) -> list[MinValueValidator, MaxValueValidator]:
        """Checks optional limit specification and generates validators for django FloatField"""
        validators = []
        try:
            validators.append(MinValueValidator(limits[0]))
        except IndexError:
            pass
        try:
            validators.append(MaxValueValidator(limits[1]))
        except IndexError:
            pass
        return validators

    def __init__(self, *args, **kwargs):
        super(SimpleWaterQualityForm, self).__init__(*args, **kwargs)
        for field, label, non_detectable, *limits in self.PARAMETER_CHOICES:
            validators = self.__set_validators(limits)
            self.fields[field] = forms.FloatField(
                label=label,
                required=False,
                validators=validators,
            )
            if non_detectable:
                self.fields[f"{field}_nondetect"] = forms.BooleanField(
                    required=False,
                )


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


class SitePhotosForm(forms.Form):
    siteimage1 = forms.ImageField(required=False, label="Site Photo")
    siteimage2 = forms.ImageField(required=False, label="Site Photo")
    siteimage3 = forms.ImageField(required=False, label="Site Photo")
    siteimage4 = forms.ImageField(required=False, label="Site Photo")


class MacroInvertebrateForm(forms.Form):
    marco_ephemeroptera = forms.IntegerField(
        required=False, min_value=0, label="Ephemeroptera (mayflies)"
    )
    marco_plecoptera = forms.IntegerField(
        required=False, min_value=0, label="Plecoptera (stoneflies)"
    )
    marco_hydropsychidae = forms.IntegerField(
        required=False,
        min_value=0,
        label="Hydropsychidae (common netspinner caddisflies)",
    )
    marco_other_caddisflies = forms.IntegerField(
        required=False, min_value=0, label="Other caddisflies"
    )
    marco_anisoptera = forms.IntegerField(
        required=False, min_value=0, label="Anisoptera (dragonflies)"
    )
    marco_zygoptera = forms.IntegerField(
        required=False, min_value=0, label="Zygoptera (damselflies)"
    )
    marco_corydalidae = forms.IntegerField(
        required=False, min_value=0, label="Corydalidae (hellgrammites)"
    )
    marco_sialidae = forms.IntegerField(
        required=False, min_value=0, label="Sialidae (alderflies)"
    )
    marco_coleoptera = forms.IntegerField(
        required=False, min_value=0, label="Coleoptera (beetles)"
    )
    marco_athericidae = forms.IntegerField(
        required=False, min_value=0, label="Athericidae (watersnipe flies)"
    )
    marco_chironomidae = forms.IntegerField(
        required=False, min_value=0, label="Chironomidae (midges)"
    )
    marco_simuliidae = forms.IntegerField(
        required=False, min_value=0, label="Simuliidae (black flies)"
    )
    marco_tipulidae = forms.IntegerField(
        required=False, min_value=0, label="Tipulidae (crane flies)"
    )
    marco_other_diptera = forms.IntegerField(
        required=False, min_value=0, label="Other diptera"
    )
    marco_amphipoda = forms.IntegerField(
        required=False, min_value=0, label="Amphipoda (scuds)"
    )
    marco_isopoda = forms.IntegerField(
        required=False, min_value=0, label="Isopoda (aquatic sow bugs)"
    )
    marco_decapoda = forms.IntegerField(
        required=False, min_value=0, label="Decapoda (crayfish)"
    )
    marco_oligochaeta = forms.IntegerField(
        required=False, min_value=0, label="Oligochaeta (aquatic worms)"
    )
    marco_hirudinea = forms.IntegerField(
        required=False, min_value=0, label="Hirudinea (leeches)"
    )
    marco_turbellaria = forms.IntegerField(
        required=False, min_value=0, label="Turbellaria (planarians)"
    )
    marco_gastropoda = forms.IntegerField(
        required=False, min_value=0, label="Gastropoda (snails)"
    )
    marco_sphaeriidae = forms.IntegerField(
        required=False, min_value=0, label="Sphaeriidae (fingernail clams)"
    )
