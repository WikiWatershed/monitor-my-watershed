# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model
from django.forms import NumberInput
from django.forms.widgets import HiddenInput

from dataloader.models import Organization, Affiliation, EquipmentModel, Medium, OrganizationType, SiteType, Variable, Unit
from django import forms

from dataloaderinterface.models import SiteRegistration, SiteAlert, SiteSensor, SensorOutput

allowed_site_types = [
    'Borehole', 'Ditch', 'Atmosphere', 'Estuary', 'House', 'Land', 'Pavement', 'Stream', 'Spring',
    'Lake, Reservoir, Impoundment', 'Laboratory or sample-preparation area', 'Observation well', 'Soil hole',
    'Storm sewer', 'Stream gage', 'Tidal stream', 'Water quality station', 'Weather station', 'Wetland', 'Other'
]


class SiteTypeSelect(forms.Select):
    site_types = None

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super(SiteTypeSelect, self).create_option(name, value, label, selected, index, subindex, attrs)
        #ModelChoiceIteratorValue not hashable work around
        #TECHDEPT - PRT flagging for likely place code will break in future updates of django 
        if isinstance(value, forms.models.ModelChoiceIteratorValue):
            value = value.value

        # this is thread-safe under CPython
        if SiteTypeSelect.site_types is None:
            SiteTypeSelect.site_types = {
                name: definition
                for (name, definition)
                in SiteType.objects.filter(name__in=allowed_site_types).values_list('name', 'definition')
            }

        option['attrs']['title'] = SiteTypeSelect.site_types.get(value, '')
        return option


class SampledMediumField(forms.ModelChoiceField):
    custom_labels = {
        'Liquid aqueous': 'Water - Liquid Aqueous'
    }

    @staticmethod
    def get_custom_label(medium):
        return SampledMediumField.custom_labels[medium] if medium in SampledMediumField.custom_labels else medium

    def label_from_instance(self, obj):
        return SampledMediumField.get_custom_label(obj.name)


class SiteRegistrationForm(forms.ModelForm):
    organization_id = forms.ChoiceField(
        choices = [],
        required=True,
        help_text="Select the organization that deployed or manages the site",
        label="Deploy Site For",
    )
    site_type = forms.ModelChoiceField(
        queryset=SiteType.objects.filter(name__in=allowed_site_types),
        help_text='Select the type of site you are deploying (e.g., "Stream")',
        widget=SiteTypeSelect
    )

    def clean_affiliation_id(self):
        return self.data['affiliation_id'] if 'affiliation_id' in self.data else None

    def clean_site_type(self):
        return self.data['site_type']

    class Meta:
        model = SiteRegistration
        fields = [
            'affiliation_id', 'sampling_feature_code', 'sampling_feature_name', 'latitude', 'longitude', 'elevation_m',
            'elevation_datum', 'site_type', 'stream_name', 'major_watershed', 'sub_basin', 'closest_town', 'site_notes'
        ]
        labels = {
            'sampling_feature_code': 'Site Code',
            'sampling_feature_name': 'Site Name',
            'elevation_m': 'Elevation',
            'site_notes': 'Notes'
        }
        help_texts = {
            'sampling_feature_code': 'Enter a brief and unique text string to identify your site (e.g., "Del_Phil")',
            'sampling_feature_name': 'Enter a brief but descriptive name for your site (e.g., "Delaware River near Phillipsburg")',
            'latitude': 'Enter the latitude of your site in decimal degrees (e.g., 40.6893)',
            'longitude': 'Enter the longitude of your site in decimal degrees (e.g., -75.2033)',
            'elevation_m': 'Enter the elevation of your site in meters',
            'elevation_datum': 'Choose the elevation datum for your site\'s elevation. If you don\'t know it, choose "MSL"',
        }


class OrganizationForm(forms.ModelForm):
    use_required_attribute = False
    organization_type = forms.ModelChoiceField(queryset=OrganizationType.objects.all().exclude(name__in=['Vendor', 'Manufacturer']), required=False, help_text='Choose the type of organization')

    class Meta:
        model = Organization
        help_texts = {
            'organization_code': 'Enter a brief, but unique code to identify your organization (e.g., "USU" or "USGS")',
            'organization_name': 'Enter the name of your organization',
            'organization_description': 'Enter a description for your organization',
            'organization_link': 'Enter a URL that links to the organization website'
        }
        fields = [
            'organization_code',
            'organization_name',
            'organization_type',
            'organization_description',
            'organization_link'
        ]


class SiteSensorForm(forms.ModelForm):
    allowed_sampled_medium = ['Air', 'Soil', 'Sediment', 'Liquid aqueous', 'Equipment', 'Not applicable', 'Other']

    id = forms.CharField(widget=HiddenInput(), required=False)
    registration = forms.CharField(widget=HiddenInput())
    output_variable = forms.CharField(widget=HiddenInput())
    result_id = forms.CharField(widget=HiddenInput(), required=False)
    result_uuid = forms.CharField(widget=HiddenInput(), required=False)

    sensor_manufacturer = forms.ModelChoiceField(queryset=Organization.objects.only_vendors(), label='Sensor Manufacturer', help_text='Choose the manufacturer', to_field_name='organization_code')
    sensor_model = forms.ModelChoiceField(queryset=EquipmentModel.objects.all(), label='Sensor Model', help_text='Choose the model of your sensor')
    variable = forms.ModelChoiceField(queryset=Variable.objects.all(), label='Measured Variable', help_text='Choose the measured variable')
    unit = forms.ModelChoiceField(queryset=Unit.objects.all(), label='Units', help_text='Choose the measured units')
    sampled_medium = SampledMediumField(queryset=Medium.objects.filter(pk__in=allowed_sampled_medium), label='Sampled Medium', help_text='Choose the sampled medium')

    def clean_registration(self):
        data = self.data['registration']
        if not data:
            raise forms.ValidationError(message='Site Registration id is required.')
        try:
            instance = SiteRegistration.objects.get(pk=data)
        except SiteRegistration.DoesNotExist:
            raise forms.ValidationError(message='Site Registration not found.')
        return instance

    def clean_output_variable(self):
        data = self.data['output_variable']
        if not data:
            raise forms.ValidationError(message='Output variable id is required.')
        try:
            instance = SensorOutput.objects.get(pk=data)
        except SensorOutput.DoesNotExist:
            raise forms.ValidationError(message='Output variable not found.')
        return instance

    class Meta:
        model = SiteSensor
        fields = [
            'output_variable', 'sensor_manufacturer', 'sensor_model', 'variable', 'unit', 'sampled_medium', 'height', 'sensor_notes'
        ]
        labels = {
            'height': 'Height above(+) or below(-) surface, in meters',
            'sensor_notes': 'Notes'
        }


class SiteAlertForm(forms.ModelForm):
    notify = forms.BooleanField(required=False, initial=False, label='Notify me if site stops receiving sensor data.')
    hours_threshold = forms.DurationField(required=False, label='Notify after', widget=NumberInput(attrs={'min': 1}))
    suffix = ' hours of site inactivity.'

    class Meta:
        model = SiteAlert
        fields = ['notify', 'hours_threshold']
        labels = {
            'notify': 'Receive email notifications for this site',
        }


class SensorDataForm(forms.Form):
    data_file = forms.FileField()
