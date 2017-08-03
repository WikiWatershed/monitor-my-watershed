from dataloader.models import People, Organization, Affiliation, EquipmentModel, Variable, Unit, TimeSeriesResultValue, \
    TimeSeriesResult
from rest_framework import serializers


class VariableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Variable
        fields = ['variable_id']


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = ['unit_id']


class EquipmentModelSerializer(serializers.ModelSerializer):
    output_variables = VariableSerializer(read_only=True, required=False, many=True)
    output_units = UnitSerializer(read_only=True, required=False, many=True)

    class Meta:
        model = EquipmentModel
        fields = ['output_variables', 'output_units']


class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = People
        fields = '__all__'


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = '__all__'


class AffiliationSerializer(serializers.ModelSerializer):
    person = PersonSerializer(required=False)
    organization = OrganizationSerializer(required=False)

    class Meta:
        model = Affiliation
        fields = '__all__'
