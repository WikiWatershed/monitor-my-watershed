from dataloaderinterface.models import SiteRegistration
from django.views.generic.edit import UpdateView, CreateView, DeleteView, FormView, BaseDetailView
from django.views.generic.detail import DetailView
from django.shortcuts import reverse, redirect
from django.http import HttpResponse
from django.http import response
from django.contrib.auth.decorators import login_required
import django

from formtools.wizard.views import SessionWizardView
from streamwatch import forms 
from streamwatch import models

from typing import List
import csv
import datetime

class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls):
        return login_required(super(LoginRequiredMixin, cls).as_view())


class StreamWatchListUpdateView(LoginRequiredMixin, DetailView):
    template_name = 'dataloaderinterface/manage_streamwatch.html'
    model = SiteRegistration
    slug_field = 'sampling_feature_code'
    slug_url_kwarg = 'sampling_feature_code'

    def dispatch(self, request, *args, **kwargs) -> HttpResponse:
        site = SiteRegistration.objects.get(sampling_feature_code=self.kwargs[self.slug_field])
        if request.user.is_authenticated and not request.user.can_administer_site(site):
            raise response.Http404
        return super(StreamWatchListUpdateView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(StreamWatchListUpdateView, self).get_context_data(**kwargs)

        sampling_feature_code = self.kwargs[self.slug_field]
        surveys = models.samplingfeature_assessments(sampling_feature_code)
        context['streamwatchsurveys'] = surveys
        return context

def condition_cat(wizard):
    setup_data = wizard.get_cleaned_data_for_step('setup')
    if setup_data is not None:
        return 'chemical' in setup_data['assessment_type']
    return True

def condition_school(wizard):
    setup_data = wizard.get_cleaned_data_for_step('setup')
    if setup_data is not None:
        return 'school' in setup_data['assessment_type']
    return True

class CreateView(SessionWizardView):
    form_list = [
        ('setup',forms.SetupForm), 
        ('conditions',forms.VisualAssessmentForm),
        ('simplecat',forms.SimpleWaterQualityForm),
        ('school',forms.SimpleHabitatAssessmentForm),
    ]
    condition_dict = {
        'simplecat': condition_school,
        'school': condition_school
    }
    
    template_name = 'streamwatch/streamwatch_wizard.html'
    slug_field = 'sampling_feature_code'
            
    def get_context_data(self, form:django.forms.Form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        context[self.slug_field] = self.kwargs[self.slug_field]
        return context

    def done(self, form_list:List[django.forms.Form], **kwargs):
        sampling_feature_id = models.sampling_feature_code_to_id(self.kwargs[self.slug_field])
        
        form_data = {'sampling_feature_id':sampling_feature_id, 'cat_methods':[]}
        for form in form_list: 
            if isinstance(form,forms.WaterQualityForm):
                form_data['cat_methods'].append(form.clean_data())    
                continue
            form_data.update(form.cleaned_data)
        adapter = models.StreamWatchODM2Adapter.from_dict(form_data)

        return redirect(reverse('streamwatches', kwargs={self.slug_field: self.kwargs[self.slug_field]}))

class UpdateView(CreateView):
    def get(self, request, *args, **kwargs):
        if 'pk' in kwargs.keys():
            # htao temp hard coded data to prove concept of dynamic loading initial values
            self.initial_dict['simplecat'] = {'simple_water_temperature': 21}
            self.initial_dict['setup'] = {'investigator1': 'John Isner'}
            self.initial_dict['conditions'] = {'weather_cond': 378}
        
        return super().get(request, *args, **kwargs)
    
    def done(self, form_list:List[django.forms.Form], **kwargs):
        sampling_feature_id = models.sampling_feature_code_to_id(self.kwargs[self.slug_field])
        
        form_data = {'sampling_feature_id':sampling_feature_id, 'cat_methods':[]}
        for form in form_list: 
            if isinstance(form,forms.WaterQualityForm):
                form_data['cat_methods'].append(form.clean_data())    
                continue
            form_data.update(form.cleaned_data)
        adapter = models.StreamWatchODM2Adapter.from_dict(form_data)

        return redirect(reverse('streamwatches', kwargs={self.slug_field: self.kwargs[self.slug_field]}))

    
class StreamWatchDetailView(DetailView):
    template_name = 'streamwatch/streamwatch_detail.html'
    slug_field = 'sampling_feature_code'
    context_object_name ='streamwatch'

    def get_object(self, queryset=None):
        sampling_feature_id = models.sampling_feature_code_to_id(self.kwargs[self.slug_field])
        action_id = int(self.kwargs['pk'])
        adapter = models.StreamWatchODM2Adapter.from_action_id(sampling_feature_id, action_id)
        data = adapter.to_dict(string_format=True)
        return data
    
    def get_context_data(self, **kwargs):
        context = super(StreamWatchDetailView, self).get_context_data(**kwargs)

        registration = SiteRegistration.objects.get(sampling_feature_code=self.kwargs[self.slug_field])
        user = self.request.user
        context['can_administer_site'] = user.is_authenticated and user.can_administer_site(registration)
        context['is_site_owner'] = self.request.user == registration.django_user
        context['sampling_feature_code'] = self.kwargs[self.slug_field]
        return context
        

class DeleteView(LoginRequiredMixin, DeleteView):
    slug_field = 'sampling_feature_code'

    def post(self, request, *args, **kwargs):
        feature_action_id = request.POST.get('id')
        models.delete_streamwatch_assessment(feature_action_id) 
        return HttpResponse('Assessment deleted successfully', status=202)

# add a streamwatch meas to CAT assessment

parameter_formset=django.forms.formset_factory(forms.WaterQualityParametersForm, extra=4)
class StreamWatchCreateMeasurementView(FormView):
    form_class = forms.WaterQualityForm
    template_name = 'streamwatch/streamwatch_sensor.html'
    slug_field = 'sampling_feature_code'
    object = None
    
    def form_invalid(self, measurement_form, parameter_forms):
        context = self.get_context_data(form=measurement_form, parameter_forms=parameter_forms)
        return self.render_to_response(context)
    
    def get_context_data(self, **kwargs):
            # if 'leafpack_form' is in kwargs, that means self.form_invalid was most likely called due to a failed POST request
        if 'form' in kwargs:
            self.object = kwargs['form']

        context = super(StreamWatchCreateMeasurementView, self).get_context_data(**kwargs)

        context[self.slug_field] = self.kwargs[self.slug_field]

        if self.object is None:
            site_registration = SiteRegistration.objects.get(sampling_feature_code=self.kwargs[self.slug_field])
            context['form'] = forms.WaterQualityForm(initial={'site_registration': site_registration}, prefix='meas')
            context['parameter_forms'] = parameter_formset(prefix ='para')

        return context
    
    def post(self, request, *args, **kwargs):
            
        # to do: implement save current streamWatch assessment
        
        form = forms.WaterQualityForm(request.POST, prefix='meas')
        parameter_forms = parameter_formset(request.POST, prefix='para')
        if form.is_valid() and parameter_forms.is_valid():
            # process the data …
            #leafpack = self.get_object()
            #leafpack.save()

            
            return redirect(reverse('streamwatches', kwargs={self.slug_field: self.kwargs[self.slug_field]}))
        else:
            
            return self.form_invalid(form, parameter_forms)

def download_StreamWatch_csv(request, sampling_feature_code, pk):
    """
    Download handler that uses csv_writer.py to parse out a StreamWatch assessment into a csv file.

    :param request: the request object
    :param sampling_feature_code: the first URL parameter
    :param pk: the second URL parameter and id of the leafpack experiement to download 
    """
    DEFAULT_DASH_LENGTH = 20
    HYPERLINK_BASE_URL = 'https://monitormywatershed.org'

    action_id = int(pk)
    
    sampling_feature_id = models.sampling_feature_code_to_id(sampling_feature_code)
    survey_data = models.StreamWatchODM2Adapter.from_action_id(sampling_feature_id, action_id)
    site = SiteRegistration.objects.get(sampling_feature_code=sampling_feature_code)
    
    filename = '{}_{}_{:03d}.csv'.format(sampling_feature_code,
                                         datetime.datetime.now(), action_id)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)

    writer = csv.writer(response)
    
    # Write file header
    writer.writerow(['StreamWatch Survey Details'])
    writer.writerow(['These data were copied to HydroShare from the WikiWatershed Data Sharing Portal.'])
    writer.writerow(['-' * DEFAULT_DASH_LENGTH])
    writer.writerow([])

    # write site registration information
    #writer.make_header(['Site Information'])
    writer.writerow(['Site Information'])
    writer.writerow(['-' * DEFAULT_DASH_LENGTH])

    writer.writerow(['Site Code', site.sampling_feature_code])
    writer.writerow(['Site Name', site.sampling_feature_name])
    writer.writerow(['Site Description', site.sampling_feature.sampling_feature_description])
    writer.writerow(['Latitude', site.latitude])
    writer.writerow(['Longitude', site.longitude])
    writer.writerow(['Elevation (m)', site.elevation_m])
    writer.writerow(['Vertical Datum', site.sampling_feature.elevation_datum])
    writer.writerow(['Site Type', site.site_type])

    writer.writerow([])

    # write streamwatch data
    # todo: separate into different activities:
    writer.writerow(['StreamWatch Survey Details'])
    writer.writerow(['-' * DEFAULT_DASH_LENGTH])

    for key, value in survey_data.items():
        writer.writerow([key.title(), value])
    
    writer.writerow(['URL', '{0}/sites/{1}/streamwatch/{2}'.format(HYPERLINK_BASE_URL,
                                                     sampling_feature_code,
                                                     action_id)])

    return response
