from django.contrib import admin
from django import forms
from django.db.models.expressions import F

from dataloader.models import *


# Register your models here.
from dataloaderinterface.forms import SiteSensorForm
from dataloaderinterface.models import SiteRegistration, SiteSensor, SensorOutput
from hydroshare.models import HydroShareAccount, HydroShareResource
from leafpack.models import LeafPack, LeafPackType, Macroinvertebrate


def update_sensor_data(obj, form, sensor_fields):
    old_object = obj.__class__.objects.get(pk=obj.pk)
    old_data = {field: getattr(old_object, field) for field in sensor_fields}
    new_data = {field: getattr(obj, field) for field in form.changed_data}
    SensorOutput.objects.annotate(equipment_model_id=F('model_id')).filter(**old_data).update(**new_data)


@admin.register(SiteSensor)
class SiteSensorAdmin(admin.ModelAdmin):
    pass


@admin.register(SiteRegistration)
class SiteRegistrationAdmin(admin.ModelAdmin):
    pass


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    pass


@admin.register(EquipmentModel)
class EquipmentModelAdmin(admin.ModelAdmin):
    sensor_fields = ['equipment_model_id']

    def save_model(self, request, obj, form, change):
        if change:
            update_sensor_data(obj, form, self.sensor_fields)

        super(EquipmentModelAdmin, self).save_model(request, obj, form, change)


@admin.register(Variable)
class VariableAdmin(admin.ModelAdmin):
    sensor_fields = ['variable_id']

    def save_model(self, request, obj, form, change):
        if change:
            update_sensor_data(obj, form, self.sensor_fields)

        super(VariableAdmin, self).save_model(request, obj, form, change)


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    sensor_fields = ['unit_id']

    def save_model(self, request, obj, form, change):
        if change:
            update_sensor_data(obj, form, self.sensor_fields)

        super(UnitAdmin, self).save_model(request, obj, form, change)


@admin.register(InstrumentOutputVariable)
class InstrumentOutputVariableAdmin(admin.ModelAdmin):
    def get_changelist_form(self, request, **kwargs):
        return super(InstrumentOutputVariableAdmin, self).get_changelist_form(request, **kwargs)

    def save_model(self, request, obj, form, change):
        super(InstrumentOutputVariableAdmin, self).save_model(request, obj, form, change)

        # There is no more time to work on having this form create user-specified SensorOutputs.
        # It creates all possible sensor outputs, so it works as before with just the instrument output variables,
        # but everything is ready to work with specific sampled media.
        if change:
            SensorOutput.objects.filter(instrument_output_variable_id=obj.pk).update(
                model_id=obj.model.equipment_model_id,
                model_name=obj.model.model_name,
                model_manufacturer=obj.model.model_manufacturer.organization_code,
                variable_id=obj.variable.variable_id,
                variable_name=obj.variable.variable_name_id,
                variable_code=obj.variable.variable_code,
                unit_id=obj.instrument_raw_output_unit.unit_id,
                unit_name=obj.instrument_raw_output_unit.unit_name,
                unit_abbreviation=obj.instrument_raw_output_unit.unit_abbreviation,
            )
        else:
            sampled_media = SiteSensorForm.allowed_sampled_medium
            sensor_outputs = [
                SensorOutput(
                    instrument_output_variable_id=obj.pk,
                    model_id=obj.model.equipment_model_id,
                    model_name=obj.model.model_name,
                    model_manufacturer=obj.model.model_manufacturer.organization_code,
                    variable_id=obj.variable.variable_id,
                    variable_name=obj.variable.variable_name_id,
                    variable_code=obj.variable.variable_code,
                    unit_id=obj.instrument_raw_output_unit.unit_id,
                    unit_name=obj.instrument_raw_output_unit.unit_name,
                    unit_abbreviation=obj.instrument_raw_output_unit.unit_abbreviation,
                    sampled_medium=sampled_medium
                )
                for sampled_medium in sampled_media
            ]
            SensorOutput.objects.bulk_create(sensor_outputs)


class SensorOutputForm(forms.ModelForm):
    model_id = forms.ModelChoiceField(queryset=EquipmentModel.objects.all(), label='Equipment Model')
    variable_id = forms.ModelChoiceField(queryset=Variable.objects.all(), label='Variable')
    unit_id = forms.ModelChoiceField(queryset=Unit.objects.all(), label='Unit')
    sampled_medium = forms.ModelChoiceField(queryset=Medium.objects.all(), label='Sampled Medium')

    def clean_model_id(self):
        return self.data['model_id']

    def clean_variable_id(self):
        return self.data['variable_id']

    def clean_unit_id(self):
        return self.data['unit_id']

    class Meta:
        model = SensorOutput
        fields = ['model_id', 'variable_id', 'unit_id', 'sampled_medium']


class HydroShareResourceInline(admin.TabularInline):
    model = HydroShareResource


@admin.register(HydroShareAccount)
class HydroShareAccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'ext_id', 'username', 'resources')
    fields = ('ext_id', 'token')


@admin.register(HydroShareResource)
class HydroShareResourceAdmin(admin.ModelAdmin):
    pass


@admin.register(LeafPack)
class LeafPackAdmin(admin.ModelAdmin):
    pass


@admin.register(LeafPackType)
class LeafPackTypeAdmin(admin.ModelAdmin):
    pass


@admin.register(Macroinvertebrate)
class MacroinvertebrateAdmin(admin.ModelAdmin):

    list_display = ('scientific_name', 'pollution_tolerance', 'common_name')

    def get_queryset(self, request):
        queryset = super(MacroinvertebrateAdmin, self).get_queryset(request)
        return queryset.order_by('pollution_tolerance')
