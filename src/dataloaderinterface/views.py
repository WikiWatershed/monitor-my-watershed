from datetime import datetime
from uuid import uuid4

from django.conf import settings
from django.db.models.aggregates import Max
from django.db.models.expressions import F
from django.db.models.query import Prefetch

from dataloader.models import FeatureAction, Result, ProcessingLevel, TimeSeriesResult, SamplingFeature, \
    SpatialReference, \
    ElevationDatum, SiteType, ActionBy, Action, Method, DataLoggerProgramFile, DataLoggerFile, \
    InstrumentOutputVariable, DataLoggerFileColumn, TimeSeriesResultValue
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse, reverse_lazy
from django.http.response import HttpResponseRedirect, Http404
from django.shortcuts import render
# Create your views here.
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import UpdateView, CreateView, DeleteView
from django.views.generic.list import ListView

from dataloaderinterface.forms import SamplingFeatureForm, ResultFormSet, SiteForm, UserRegistrationForm, \
    OrganizationForm, UserUpdateForm, ActionByForm, SiteAlertForm
from dataloaderinterface.models import ODM2User, SiteRegistration, SiteSensor, SiteAlert


class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls):
        return login_required(super(LoginRequiredMixin, cls).as_view())


class HomeView(TemplateView):
    template_name = 'dataloaderinterface/index.html'

    # def get_context_data(self, **kwargs):
    #     context = super(HomeView, self).get_context_data()
    #     context['device_results'] = []
    #     for device in DeviceRegistration.objects.get_queryset().filter(user=self.request.user.id):
    #         sampling_feature = SamplingFeature.objects.get(sampling_feature_uuid__exact=device.deployment_sampling_feature_uuid)
    #         feature_actions = sampling_feature.feature_actions.prefetch_related('results__timeseriesresult__values', 'results__variable').all()
    #         context['device_results'].append({'device': device, 'feature_actions': feature_actions})
    #     return context


class UserUpdateView(UpdateView):
    form_class = UserUpdateForm
    template_name = 'registration/account.html'

    def get_object(self, queryset=None):
        return self.request.user

    def get_form(self, form_class=None):
        user = self.get_object()
        organization = user.odm2user.affiliation.organization
        form = UserUpdateForm(instance=user, initial={'organization': organization})
        return form

    def get_context_data(self, **kwargs):
        context = super(UserUpdateView, self).get_context_data(**kwargs)
        context['organization_form'] = OrganizationForm()
        return context

    def post(self, request, *args, **kwargs):
        user = User.objects.get(pk=request.user.pk)
        form = UserUpdateForm(request.POST, instance=user, initial={'organization': user.odm2user.affiliation.organization})
        if form.is_valid():
            form.save()
            messages.success(request, 'Your information has been updated successfully.')
            return HttpResponseRedirect(reverse('user_account'))
        else:
            messages.error(request, 'There were some errors in the form.')
            return render(request, self.template_name, {'form': form, 'organization_form': OrganizationForm()})


class UserRegistrationView(CreateView):
    template_name = 'registration/register.html'
    form_class = UserRegistrationForm
    success_url = reverse_lazy('home')

    def get_context_data(self, **kwargs):
        context = super(UserRegistrationView, self).get_context_data(**kwargs)
        context['organization_form'] = OrganizationForm()
        return context

    def post(self, request, *args, **kwargs):
        response = super(UserRegistrationView, self).post(request, *args, **kwargs)
        form = self.get_form()

        if form.instance.id:
            login(request, form.instance)

        return response


class SitesListView(LoginRequiredMixin, ListView):
    model = SiteRegistration
    context_object_name = 'sites'
    template_name = 'dataloaderinterface/my-sites.html'

    def get_queryset(self):
        return super(SitesListView, self).get_queryset()\
            .filter(django_user_id=self.request.user.id)\
            .prefetch_related('sensors')\
            .annotate(latest_measurement=Max('sensors__last_measurement_datetime'))

    def get_context_data(self, **kwargs):
        context = super(SitesListView, self).get_context_data()
        context['followed_sites'] = self.request.user.followed_sites\
            .prefetch_related('sensors')\
            .annotate(latest_measurement=Max('sensors__last_measurement_datetime'))\
            .all()
        return context


class StatusListView(ListView):
    model = SiteRegistration
    context_object_name = 'sites'
    template_name = 'dataloaderinterface/status.html'

    def get_queryset(self):
        return super(StatusListView, self).get_queryset()\
            .filter(django_user_id=self.request.user.id)\
            .prefetch_related(Prefetch('sensors', queryset=SiteSensor.objects.filter(variable_code__in=[
                'EnviroDIY_Mayfly_Volt',
                'EnviroDIY_Mayfly_Temp',
                'EnviroDIY_Mayfly_FreeSRAM'
            ]), to_attr='status_sensors')) \
            .annotate(latest_measurement=Max('sensors__last_measurement_datetime'))

    def get_context_data(self, **kwargs):
        context = super(StatusListView, self).get_context_data(**kwargs)
        context['followed_sites'] = self.request.user.followed_sites \
            .prefetch_related(Prefetch('sensors', queryset=SiteSensor.objects.filter(variable_code__in=[
                'EnviroDIY_Mayfly_Volt',
                'EnviroDIY_Mayfly_Temp',
                'EnviroDIY_Mayfly_FreeSRAM'
            ]), to_attr='status_sensors'))
        return context


class BrowseSitesListView(ListView):
    model = SiteRegistration
    context_object_name = 'sites'
    template_name = 'dataloaderinterface/browse-sites.html'

    def get_queryset(self):
        return super(BrowseSitesListView, self).get_queryset()\
            .prefetch_related('sensors')\
            .annotate(latest_measurement=Max('sensors__last_measurement_datetime'))


class SiteDetailView(DetailView):
    model = SiteRegistration
    context_object_name = 'site'
    slug_field = 'sampling_feature_code'
    slug_url_kwarg = 'sampling_feature_code'
    template_name = 'dataloaderinterface/site_details.html'

    def get_queryset(self):
        return super(SiteDetailView, self).get_queryset().prefetch_related('sensors')

    def get_context_data(self, **kwargs):
        context = super(SiteDetailView, self).get_context_data()
        context['tsa_url'] = settings.TSA_URL
        context['is_followed'] = self.request.user.is_authenticated and self.request.user.followed_sites.filter(sampling_feature_code=self.object.sampling_feature_code).exists()
        return context


class SiteDeleteView(LoginRequiredMixin, DeleteView):
    model = SiteRegistration
    slug_field = 'sampling_feature_code'
    slug_url_kwarg = 'sampling_feature_code'
    success_url = reverse_lazy('sites_list')

    def post(self, request, *args, **kwargs):
        site = self.get_object(self.get_queryset())
        if not site:
            raise Http404

        if request.user.id != site.django_user_id and not self.request.user.is_staff:
            raise Http404

        sampling_feature = site.sampling_feature
        data_logger_program = DataLoggerProgramFile.objects.filter(
            affiliation_id=site.affiliation_id,
            program_name__contains=sampling_feature.sampling_feature_code
        ).first()
        data_logger_file = data_logger_program.data_logger_files.first()

        feature_actions = sampling_feature.feature_actions.with_results().all()
        for feature_action in feature_actions:
            result = feature_action.results.first()
            delete_result(result)

        data_logger_file.delete()
        data_logger_program.delete()
        sampling_feature.site.delete()
        sampling_feature.delete()
        site.sensors.all().delete()
        site.delete()
        return HttpResponseRedirect(self.success_url)

    def get(self, request, *args, **kwargs):
        raise Http404


class SiteUpdateView(LoginRequiredMixin, UpdateView):
    template_name = 'dataloaderinterface/site_registration.html'
    model = SiteRegistration
    slug_field = 'sampling_feature_code'
    slug_url_kwarg = 'sampling_feature_code'
    object = None
    fields = []

    def get_success_url(self):
        print 'Getting success url'
        return reverse_lazy('site_detail', kwargs={'sampling_feature_code': self.object.sampling_feature_code})

    def get_formset_initial_data(self, *args):
        if self.get_object().django_user != self.request.user and not self.request.user.is_staff:
            raise Http404
        registration = self.get_object()
        result_form_data = [
            {
                'result_id': sensor.result_id,
                'equipment_model': sensor.equipment_model,
                'variable': sensor.variable,
                'unit': sensor.unit,
                'sampled_medium': sensor.medium
            }
            for sensor in registration.sensors.all()
        ]
        return result_form_data

    def get_context_data(self, **kwargs):
        if self.get_object().django_user != self.request.user and not self.request.user.is_staff:
            raise Http404
        context = super(SiteUpdateView, self).get_context_data()
        data = self.request.POST if self.request.POST else None
        sampling_feature = self.get_object().sampling_feature
        action_by = sampling_feature.feature_actions.first().action.action_by.first()

        site_alert = self.request.user.site_alerts\
            .filter(site_registration__sampling_feature_code=sampling_feature.sampling_feature_code)\
            .first()
        alert_data = {'notify': True, 'hours_threshold': site_alert.hours_threshold} if site_alert else {}

        context['sampling_feature_form'] = SamplingFeatureForm(data=data, instance=sampling_feature)
        context['site_form'] = SiteForm(data=data, instance=sampling_feature.site)
        context['results_formset'] = ResultFormSet(data=data, initial=self.get_formset_initial_data())
        context['action_by_form'] = ActionByForm(data=data, instance=action_by)
        context['email_alert_form'] = SiteAlertForm(data=data, initial=alert_data)
        context['zoom_level'] = data['zoom-level'] if data and 'zoom-level' in data else None
        return context

    def post(self, request, *args, **kwargs):
        if self.get_object().django_user != self.request.user and not self.request.user.is_staff:
            raise Http404
        site_registration = SiteRegistration.objects.filter(sampling_feature_code=self.kwargs['sampling_feature_code']).first()
        sampling_feature = site_registration.sampling_feature

        sampling_feature_form = SamplingFeatureForm(data=self.request.POST, instance=sampling_feature)
        site_form = SiteForm(data=self.request.POST, instance=sampling_feature.site)
        results_formset = ResultFormSet(data=self.request.POST, initial=self.get_formset_initial_data())
        action_by_form = ActionByForm(request.POST)
        notify_form = SiteAlertForm(request.POST)
        registration_form = self.get_form()

        if all_forms_valid(registration_form, sampling_feature_form, site_form, action_by_form, results_formset,
                           notify_form):
            affiliation = action_by_form.cleaned_data['affiliation'] or request.user.odm2user.affiliation
            data_logger_file = DataLoggerFile.objects.filter(data_logger_file_name=site_registration.sampling_feature_code).first()
            data_logger_program = data_logger_file.program

            # Update notification settings
            site_alert = self.request.user.site_alerts.filter(site_registration=site_registration).first()

            if notify_form.cleaned_data['notify'] and site_alert:
                site_alert.hours_threshold = notify_form['hours_threshold'].value()
                site_alert.save()

            elif notify_form.cleaned_data['notify'] and not site_alert:
                self.request.user.site_alerts.create(
                    site_registration=site_registration,
                    hours_threshold=notify_form.cleaned_data['hours_threshold']
                )

            elif not notify_form.cleaned_data['notify'] and site_alert:
                site_alert.delete()

            # Update sampling feature
            sampling_feature_form.instance.save()

            # Update Site
            site_form.instance.save()

            # Update datalogger program and datalogger file names
            data_logger_program.program_name = '%s' % sampling_feature.sampling_feature_code
            data_logger_program.affiliation = affiliation
            data_logger_program.save()

            data_logger_file.data_logger_file_name = '%s' % sampling_feature.sampling_feature_code
            data_logger_file.save()

            # Update Site Registration
            site_registration.affiliation_id = affiliation.affiliation_id
            site_registration.django_user = User.objects.filter(odm2user__affiliation_id=affiliation.affiliation_id).first()
            site_registration.person = str(affiliation.person)
            site_registration.organization = str(affiliation.organization)
            site_registration.sampling_feature_code = sampling_feature.sampling_feature_code
            site_registration.sampling_feature_name = sampling_feature.sampling_feature_name
            site_registration.elevation_m = sampling_feature.elevation_m
            site_registration.latitude = sampling_feature.site.latitude
            site_registration.longitude = sampling_feature.site.longitude
            site_registration.site_type = sampling_feature.site.site_type_id
            registration_form.instance = site_registration
            site_registration.save()

            for result_form in results_formset.forms:
                is_new_result = 'result_id' not in result_form.initial
                to_delete = result_form['DELETE'].data

                if is_new_result and to_delete:
                    continue
                elif is_new_result:
                    create_result(site_registration, result_form, sampling_feature, affiliation, data_logger_file)
                    continue
                elif to_delete:
                    result = Result.objects.get(result_id=result_form.initial['result_id'])
                    delete_result(result)
                    continue

                # Update Result
                result = Result.objects.get(result_id=result_form.initial['result_id'])
                result.variable = result_form.cleaned_data['variable']
                result.sampled_medium = result_form.cleaned_data['sampled_medium']
                result.unit = result_form.cleaned_data['unit']
                result.save()

                # Update Data Logger file column
                instrument_output_variable = InstrumentOutputVariable.objects.filter(
                    model=result_form.cleaned_data['equipment_model'],
                    instrument_raw_output_unit=result.unit,
                    variable=result.variable,
                ).first()

                data_logger_file_column = result.data_logger_file_columns.first()
                data_logger_file_column.instrument_output_variable = instrument_output_variable
                data_logger_file_column.column_label = '%s(%s)' % (result.variable.variable_code, result.unit.unit_abbreviation)
                data_logger_file_column.save()

                # Update action by
                action_by = result.feature_action.action.action_by.first()
                action_by.affiliation = affiliation
                action_by.save()

                # Update Site Sensor
                site_sensor = SiteSensor.objects.filter(result_id=result.result_id).first()
                site_sensor.model_name = instrument_output_variable.model.model_name
                site_sensor.model_manufacturer = instrument_output_variable.model.model_manufacturer.organization_name
                site_sensor.variable_name = result.variable.variable_name_id
                site_sensor.variable_code = result.variable.variable_code
                site_sensor.unit_name = result.unit.unit_name
                site_sensor.unit_abbreviation = result.unit.unit_abbreviation
                site_sensor.sampled_medium = result.sampled_medium_id
                site_sensor.save()

            messages.success(request, 'The site has been updated successfully.')
            return self.form_valid(registration_form)
        else:
            messages.error(request, 'There are still some required fields that need to be filled out.')
            return self.form_invalid(registration_form)


class SiteRegistrationView(LoginRequiredMixin, CreateView):
    template_name = 'dataloaderinterface/site_registration.html'
    model = SiteRegistration
    object = None
    fields = []

    def get_success_url(self):
        return reverse_lazy('site_detail', kwargs={'sampling_feature_code': self.object.sampling_feature_code})

    @staticmethod
    def get_default_data():
        data = {
            'elevation_datum': ElevationDatum.objects.filter(pk='MSL').first(),
            'site_type': SiteType.objects.filter(pk='Stream').first()
        }
        return data

    def get_context_data(self, **kwargs):
        default_data = self.get_default_data()
        context = super(SiteRegistrationView, self).get_context_data()
        data = self.request.POST if self.request.POST else None
        context['sampling_feature_form'] = SamplingFeatureForm(data, initial=default_data)
        context['site_form'] = SiteForm(data, initial=default_data)
        context['results_formset'] = ResultFormSet(data)
        context['action_by_form'] = ActionByForm(data)
        context['email_alert_form'] = SiteAlertForm(data)
        context['zoom_level'] = data['zoom-level'] if data and 'zoom-level' in data else None
        return context

    def post(self, request, *args, **kwargs):
        sampling_feature_form = SamplingFeatureForm(request.POST)
        site_form = SiteForm(request.POST)
        results_formset = ResultFormSet(request.POST)
        action_by_form = ActionByForm(request.POST)
        notify_form = SiteAlertForm(request.POST)
        registration_form = self.get_form()

        if all_forms_valid(registration_form, sampling_feature_form, site_form, action_by_form, results_formset, notify_form):
            affiliation = action_by_form.cleaned_data['affiliation'] or request.user.odm2user.affiliation

            # Create sampling feature
            sampling_feature = sampling_feature_form.instance
            sampling_feature.sampling_feature_type_id = 'Site'
            sampling_feature.save()

            # Create Site
            site = site_form.instance
            site.sampling_feature = sampling_feature
            site.spatial_reference = SpatialReference.objects.get(srs_name='WGS84')
            site.save()

            # Create Data Logger file
            data_logger_program = DataLoggerProgramFile.objects.create(
                affiliation=affiliation,
                program_name='%s' % sampling_feature.sampling_feature_code
            )

            data_logger_file = DataLoggerFile.objects.create(
                program=data_logger_program,
                data_logger_file_name='%s' % sampling_feature.sampling_feature_code
            )

            # Create Site Registration TODO: maybe do it in another function.
            registration_data = {
                'registration_token': uuid4(),
                'registration_date': datetime.now(),
                'django_user': User.objects.filter(odm2user__affiliation_id=affiliation.affiliation_id).first(),
                'affiliation_id': affiliation.affiliation_id,
                'person': str(affiliation.person),
                'organization': str(affiliation.organization),
                'sampling_feature_id': sampling_feature.sampling_feature_id,
                'sampling_feature_code': sampling_feature.sampling_feature_code,
                'sampling_feature_name': sampling_feature.sampling_feature_name,
                'elevation_m': sampling_feature.elevation_m,
                'latitude': sampling_feature.site.latitude,
                'longitude': sampling_feature.site.longitude,
                'site_type': sampling_feature.site.site_type_id,
            }

            site_registration = SiteRegistration(**registration_data)
            registration_form.instance = site_registration
            site_registration.save()

            if notify_form.cleaned_data['notify']:
                self.request.user.site_alerts.create(
                    site_registration=site_registration,
                    hours_threshold=notify_form.cleaned_data['hours_threshold']
                )

            for result_form in results_formset.forms:
                create_result(site_registration, result_form, sampling_feature, affiliation, data_logger_file)

            return self.form_valid(registration_form)
        else:
            messages.error(request, 'There are still some required fields that need to be filled out!')
            return self.form_invalid(registration_form)


def all_forms_valid(*forms):
    return reduce(lambda all_valid, form: all_valid and form.is_valid(), forms, True)


def create_result(site_registration, result_form, sampling_feature, affiliation, data_logger_file):
    # Create action
    action = Action(
        method=Method.objects.filter(method_type_id='Instrument deployment').first(),
        action_type_id='Instrument deployment',
        begin_datetime=datetime.utcnow(), begin_datetime_utc_offset=0
    )
    action.save()

    # Create feature action
    feature_action = FeatureAction(action=action, sampling_feature=sampling_feature)
    feature_action.save()

    # Create action by
    action_by = ActionBy(action=action, affiliation=affiliation, is_action_lead=True)
    action_by.save()

    # Create Results
    result = result_form.instance
    result.feature_action = feature_action
    result.result_type_id = 'Time series coverage'
    result.processing_level = ProcessingLevel.objects.get(processing_level_code='Raw')
    result.status_id = 'Ongoing'
    result.save()

    # Create TimeSeriesResults
    time_series_result = TimeSeriesResult(result=result)
    time_series_result.aggregation_statistic_id = 'Average'
    time_series_result.save()

    # Create Data Logger file column
    instrument_output_variable = InstrumentOutputVariable.objects.filter(
        model=result_form.cleaned_data['equipment_model'],
        variable=result_form.cleaned_data['variable'],
        instrument_raw_output_unit=result_form.cleaned_data['unit'],
    ).first()

    DataLoggerFileColumn.objects.create(
        result=result,
        data_logger_file=data_logger_file,
        instrument_output_variable=instrument_output_variable,
        column_label='%s(%s)' % (result.variable.variable_code, result.unit.unit_abbreviation)
    )

    sensor_data = {
        'result_id': result.result_id,
        'result_uuid': result.result_uuid,
        'registration': site_registration,
        'model_name': instrument_output_variable.model.model_name,
        'model_manufacturer': instrument_output_variable.model.model_manufacturer.organization_name,
        'variable_name': result.variable.variable_name_id,
        'variable_code': result.variable.variable_code,
        'unit_name': result.unit.unit_name,
        'unit_abbreviation': result.unit.unit_abbreviation,
        'sampled_medium': result.sampled_medium_id
    }

    site_sensor = SiteSensor(**sensor_data)
    site_sensor.save()

    return result


def delete_result(result):
    result_id = result.result_id
    feature_action = result.feature_action
    action = feature_action.action

    result.data_logger_file_columns.all().delete()
    result.timeseriesresult.values.all().delete()
    result.timeseriesresult.delete()

    action.action_by.all().delete()
    result.delete()

    feature_action.delete()
    action.delete()
    SiteSensor.objects.filter(result_id=result_id).delete()
