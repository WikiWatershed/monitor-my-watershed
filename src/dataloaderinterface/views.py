from datetime import datetime
from uuid import uuid4

from dataloader.models import FeatureAction, Result, ProcessingLevel, TimeSeriesResult, SamplingFeature, \
    SpatialReference, \
    ElevationDatum, SiteType, ActionBy, Action, Method, DataLoggerProgramFile, DataLoggerFile, \
    InstrumentOutputVariable, DataLoggerFileColumn
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

from dataloaderinterface.csv_serializer import SiteResultSerializer
from dataloaderinterface.forms import SamplingFeatureForm, ResultFormSet, SiteForm, UserRegistrationForm, \
    OrganizationForm, UserUpdateForm, ActionByForm
from dataloaderinterface.models import DeviceRegistration, ODM2User


class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls):
        return login_required(super(LoginRequiredMixin, cls).as_view())


class HomeView(TemplateView):
    template_name = 'dataloaderinterface/index.html'

    def get_context_data(self, **kwargs):
        context = super(HomeView, self).get_context_data()
        context['device_results'] = []
        for device in DeviceRegistration.objects.get_queryset().filter(user=self.request.user.id):
            sampling_feature = SamplingFeature.objects.get(sampling_feature_uuid__exact=device.deployment_sampling_feature_uuid)
            feature_actions = sampling_feature.feature_actions.prefetch_related('results__timeseriesresult__values', 'results__variable').all()
            context['device_results'].append({'device': device, 'feature_actions': feature_actions})
        return context


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
            return HttpResponseRedirect(reverse('home'))
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


class DevicesListView(LoginRequiredMixin, ListView):
    model = DeviceRegistration
    template_name = 'dataloaderinterface/my-sites.html'

    def get_queryset(self):
        return super(DevicesListView, self).get_queryset().filter(user_id=self.request.user.odm2user.pk)


class BrowseSitesListView(ListView):
    model = DeviceRegistration
    context_object_name = 'registrations'
    template_name = 'dataloaderinterface/browse-sites.html'

    # def get_queryset(self):
    #     return super(BrowseSitesListView, self).get_queryset().select_related('site').filter()


class DeviceDetailView(DetailView):
    slug_field = 'registration_id'
    model = DeviceRegistration
    template_name = 'dataloaderinterface/site_details.html'

    def get_context_data(self, **kwargs):
        context = super(DeviceDetailView, self).get_context_data()
        context['sampling_feature'] = self.object.sampling_feature
        context['feature_actions'] = self.object.sampling_feature.feature_actions.with_results().all()
        context['affiliation'] = self.object.user.affiliation
        context['site'] = self.object.sampling_feature.site
        return context


class SiteDeleteView(LoginRequiredMixin, DeleteView):
    model = DeviceRegistration
    slug_field = 'registration_id'
    success_url = reverse_lazy('sites_list')

    def post(self, request, *args, **kwargs):
        registration = self.get_object()
        if not registration:
            raise Http404

        if request.user != registration.user.user:
            # temporary error. TODO: do something a little bit more elaborate. or maybe not...
            raise Http404

        sampling_feature = registration.sampling_feature
        data_logger_program = DataLoggerProgramFile.objects.filter(
            affiliation=request.user.odm2user.affiliation,
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
        registration.delete()
        return HttpResponseRedirect(self.success_url)

    def get(self, request, *args, **kwargs):
        raise Http404


class SiteUpdateView(LoginRequiredMixin, UpdateView):
    template_name = 'dataloaderinterface/site_registration.html'
    model = DeviceRegistration
    slug_field = 'registration_id'
    object = None
    fields = []

    def get_success_url(self):
        return reverse_lazy('site_detail', kwargs=self.kwargs)

    def get_formset_initial_data(self, *args):
        sampling_feature = self.get_object().sampling_feature
        results = Result.objects.filter(feature_action__in=(sampling_feature.feature_actions.values_list('feature_action_id')))
        result_form_data = [
            {
                'result_id': result.result_id,
                # this is kinda ugly as shit but works. keep it to be safe, or don't in case there's results without datalogger column.
                'equipment_model': result.data_logger_file_columns.first() and result.data_logger_file_columns.first().instrument_output_variable.model,
                'variable': result.variable,
                'unit': result.unit,
                'sampled_medium': result.sampled_medium
            }
            for result in results.prefetch_related('data_logger_file_columns__instrument_output_variable__model')
        ]
        return result_form_data

    def get_context_data(self, **kwargs):
        context = super(SiteUpdateView, self).get_context_data()
        data = self.request.POST if self.request.POST else None
        sampling_feature = self.get_object().sampling_feature

        context['sampling_feature_form'] = SamplingFeatureForm(data=data, instance=sampling_feature)
        context['site_form'] = SiteForm(data=data, instance=sampling_feature.site)
        context['results_formset'] = ResultFormSet(data=data, initial=self.get_formset_initial_data())
        context['zoom_level'] = data['zoom-level'] if data and 'zoom-level' in data else None
        return context

    def post(self, request, *args, **kwargs):
        registration = DeviceRegistration.objects.filter(pk=self.kwargs['slug']).first()
        sampling_feature = registration.sampling_feature

        sampling_feature_form = SamplingFeatureForm(data=self.request.POST, instance=sampling_feature)
        site_form = SiteForm(data=self.request.POST, instance=sampling_feature.site)
        results_formset = ResultFormSet(data=self.request.POST, initial=self.get_formset_initial_data())
        registration_form = self.get_form()

        if all_forms_valid(sampling_feature_form, site_form, results_formset):
            affiliation = request.user.odm2user.affiliation
            data_logger_program = DataLoggerProgramFile.objects.filter(
                affiliation=affiliation, program_name__contains=registration.sampling_feature.sampling_feature_code
            ).first()
            data_logger_file = data_logger_program.data_logger_files.first()

            # Update sampling feature
            sampling_feature_form.instance.save()

            # Update Site
            site_form.instance.save()

            # Update datalogger program and datalogger file names
            data_logger_program.program_name = '%s data collection' % sampling_feature.sampling_feature_code
            data_logger_file.data_logger_file_name = '%s' % sampling_feature.sampling_feature_code
            data_logger_program.save()
            data_logger_file.save()

            for result_form in results_formset.forms:
                is_new_result = 'result_id' not in result_form.initial
                to_delete = result_form['DELETE'].data

                if is_new_result and to_delete:
                    continue
                elif is_new_result:
                    create_result(result_form, sampling_feature, affiliation, data_logger_file)
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

            messages.success(request, 'The site has been updated successfully.')
            return HttpResponseRedirect(self.get_success_url())
        else:
            messages.error(request, 'There are still some required fields that need to be filled out.')
            return self.form_invalid(registration_form)


class SiteRegistrationView(LoginRequiredMixin, CreateView):
    template_name = 'dataloaderinterface/site_registration.html'
    model = DeviceRegistration
    object = None
    fields = []

    def get_success_url(self):
        return reverse_lazy('site_detail', kwargs={'slug': self.object.pk})

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

        context['zoom_level'] = data['zoom-level'] if data and 'zoom-level' in data else None
        return context

    def post(self, request, *args, **kwargs):
        sampling_feature_form = SamplingFeatureForm(request.POST)
        site_form = SiteForm(request.POST)
        results_formset = ResultFormSet(request.POST)
        action_by_form = ActionByForm(request.POST)
        registration_form = self.get_form()

        if all_forms_valid(sampling_feature_form, site_form, action_by_form, results_formset):
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

            for result_form in results_formset.forms:
                create_result(result_form, sampling_feature, affiliation, data_logger_file)

            registration_form.instance.deployment_sampling_feature_uuid = sampling_feature.sampling_feature_uuid
            registration_form.instance.user = ODM2User.objects.filter(affiliation_id=affiliation.pk).first()
            registration_form.instance.authentication_token = uuid4()
            registration_form.instance.save()
            return self.form_valid(registration_form)
        else:
            messages.error(request, 'There are still some required fields that need to be filled out!')
            return self.form_invalid(registration_form)


def all_forms_valid(*forms):
    return reduce(lambda all_valid, form: all_valid and form.is_valid(), forms, True)


def create_result(result_form, sampling_feature, affiliation, data_logger_file):
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

    # Create csv file to hold the sensor data.
    # TODO: have this send a signal and the call to create the file be somewhere else.
    serializer = SiteResultSerializer(result)
    serializer.build_csv()

    return result


def delete_result(result):
    feature_action = result.feature_action
    action = feature_action.action

    result.data_logger_file_columns.all().delete()
    result.timeseriesresult.values.all().delete()
    result.timeseriesresult.delete()

    action.action_by.all().delete()
    result.delete()

    feature_action.delete()
    action.delete()
