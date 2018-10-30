from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms
from django.forms.widgets import Select

from accounts.models import User
from dataloader.models import Organization


class UserOrganizationField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.organization_name


class UserRegistrationForm(UserCreationForm):
    use_required_attribute = False

    organization_code = UserOrganizationField(
        queryset=Organization.objects.exclude_vendors().order_by('organization_name'),
        widget=Select(attrs={'id': 'id_user_organization_code'}),
        to_field_name='organization_code',
        required=False,
        help_text='Begin to enter the common name of your organization to choose from the list. '
                  'If "No results found", then clear your entry, click on the drop-down-list to select '
                  '"Add New Organization".'
    )
    agreement = forms.BooleanField(required=True)
    acceptance = forms.BooleanField(required=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username', 'organization_code']


class UserUpdateForm(UserChangeForm):
    use_required_attribute = False

    organization_code = UserOrganizationField(
        queryset=Organization.objects.exclude_vendors().order_by('organization_name'),
        to_field_name='organization_code',
        required=False,
        help_text='Begin to enter the common name of your organization to choose from the list. '
                  'If "No results found", then clear your entry, click on the drop-down-list to select '
                  '"Add New Organization".'
    )

    def save(self, commit=True):
        user = super(UserUpdateForm, self).save(commit)
        return user.save(update_fields=self.changed_data)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password', 'username', 'organization_code']
