import csv
import datetime
from typing import List, TextIO, Dict, Any

import django
from django.shortcuts import reverse, redirect
from django.http import HttpResponse
from django.http import response
from django.contrib.auth.decorators import login_required
from formtools.wizard.views import SessionWizardView

from dataloaderinterface.models import SiteRegistration
from streamwatch import models
from streamwatch import forms


class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls):
        return login_required(super(LoginRequiredMixin, cls).as_view())


class ListUpdateView(LoginRequiredMixin, django.views.generic.detail.DetailView):
    template_name = 'dataloaderinterface/manage_streamwatch.html'
    model = SiteRegistration
    slug_field = 'sampling_feature_code'
    slug_url_kwarg = 'sampling_feature_code'

    def dispatch(self, request, *args, **kwargs) -> HttpResponse:
        site = SiteRegistration.objects.get(sampling_feature_code=self.kwargs[self.slug_field])
        if request.user.is_authenticated and not request.user.can_administer_site(site.sampling_feature_id):
            raise response.Http404
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        sampling_feature_code = self.kwargs[self.slug_field]
        assessments = models.samplingfeature_assessments(sampling_feature_code)
        context['streamwatchsurveys'] = assessments
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
        ('simplehabitat',forms.SimpleHabitatAssessmentForm),
        ('simplewaterquality',forms.SimpleWaterQualityForm),        
    ]
    condition_dict = {
        'simplewaterquality': condition_school,
        'simplehabitat': condition_school
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

    PRIMARY_KEY_FIELD = 'action_id'

    def get(self, request, *args, **kwargs):
        if self.PRIMARY_KEY_FIELD in kwargs.keys():
            action_id = int(kwargs[self.PRIMARY_KEY_FIELD])
            adapter = models.StreamWatchODM2Adapter.from_action_id(action_id)
            form_data = adapter.to_dict()
            self.initial_dict['setup'] = form_data
            self.initial_dict['conditions'] = form_data
            self.initial_dict['simplewaterquality'] = form_data
            self.initial_dict['simplehabitat'] = form_data
        
        return super().get(request, *args, **kwargs)

    def get_context_data(self, form:django.forms.Form, **kwargs):
        context_data = super().get_context_data(form, **kwargs)
        if self.PRIMARY_KEY_FIELD in self.kwargs:
            context_data[self.PRIMARY_KEY_FIELD] = self.kwargs[self.PRIMARY_KEY_FIELD]
        return context_data

    def done(self, form_list:List[django.forms.Form], **kwargs):
        sampling_feature_id = models.sampling_feature_code_to_id(self.kwargs[self.slug_field])
        form_data = {'sampling_feature_id':sampling_feature_id, 'cat_methods':[]}
        for form in form_list: 
            if isinstance(form,forms.WaterQualityForm):
                form_data['cat_methods'].append(form.clean_data())    
                continue
            form_data.update(form.cleaned_data)
        
        action_id = int(self.kwargs[self.PRIMARY_KEY_FIELD])
        adapter = models.StreamWatchODM2Adapter.from_action_id(action_id)
        adapter.update_from_dict(form_data)

        return redirect(reverse('streamwatches', kwargs={self.slug_field: self.kwargs[self.slug_field]}))

    
class DetailView(django.views.generic.detail.DetailView):
    template_name = 'streamwatch/streamwatch_detail.html'
    slug_field = 'sampling_feature_code'
    context_object_name ='streamwatch'

    def get_object(self, queryset=None):
        action_id = int(self.kwargs['pk'])
        adapter = models.StreamWatchODM2Adapter.from_action_id(action_id)
        data = adapter.to_dict(string_format=True)
        return data
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        registration = SiteRegistration.objects.get(sampling_feature_code=self.kwargs[self.slug_field])
        user = self.request.user
        context['can_administer_site'] = user.is_authenticated and user.can_administer_site(registration.sampling_feature_id)
        context['is_site_owner'] = user.id == registration.django_user
        context['sampling_feature_code'] = self.kwargs[self.slug_field]
        context['action_id'] = int(self.kwargs['pk'])
        return context
        

class DeleteView(LoginRequiredMixin, django.views.generic.edit.DeleteView):
    slug_field = 'sampling_feature_code'

    def post(self, request, *args, **kwargs):
        feature_action_id = request.POST.get('id')
        models.delete_streamwatch_assessment(feature_action_id) 
        return HttpResponse('Assessment deleted successfully', status=202)


parameter_formset=django.forms.formset_factory(forms.WaterQualityParametersForm, extra=4)
class StreamWatchCreateMeasurementView(django.views.generic.edit.FormView):
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


def csv_export(request, sampling_feature_code:str, actionids:str):
    """
    Download handler that uses csv_writer.py to parse out a StreamWatch assessment into a csv file.

    :param request: the request object
    :param sampling_feature_code: the first URL parameter
    :param pk: the second URL parameter and id of the leafpack experiement to download 
    """

    def format_metadata(site:SiteRegistration) -> List[List[str]]:
        result = [
            [f'# Site Information'],
            [f'# ----------------'],
            [f'SiteCode: {site.sampling_feature_code}'],
            [f'SiteName: {site.sampling_feature_name}'],
            [f'SiteDescription: {site.sampling_feature.sampling_feature_description}'],
            [f'Latitude: {site.latitude}'],
            [f'Longitude: {site.longitude}'],
            [f'Elevation: {site.longitude}'],
            [f'VerticalDatum: {site.sampling_feature.elevation_datum}'],
            [f'SiteType: {site.site_type}'],
            [f'SiteNotes: {site.site_notes}'],
            [f'# '],
        ]
        return result

    def format_header() -> List[str]:
        parameters = [
            'Investigator_1',
            'Investigator_2',
            'Assessment_Date',
            'Assessment_Time',
            'Assessment_Types',
            'Visual_Weather',
            'Visual_Time_Since_Rainfall',
            'Visual_Water_Color',
            'Visual_Water_Odor',
            'Visual_Turbidity',
            'Visual_Water_Movement',
            'Visual_Surface_Coating',
            'Visual_Aquatic_Vegetation_Amount',
            'Visual_Aquatic_Vegetation_Type',
            'Visual_Algae_Amount',
            'Visual_Algae_Type',
            'Habitat_Woody_Debris_Amount',
            'Habitat_Woody_Debris_Type',
            'Habitat_Tree_Canopy',
            'Habitat_Land_Use',
            'Chemical_Air_Temperature_degC',
            'Chemical_Water_Temperature_degC',
            'Chemical_Nitrate_Nitrogen_ppm',
            'Chemical_Phosphates_ppm',
            'Chemical_pH',
            'Chemical_Turbidity_Sample_Size_mL',
            'Chemical_Turbidity_Amount_of_Regent_mL',
            'Chemical_Turbidity_JTU',
            'Chemical_Dissolved_Oxygen_ppm',
            'Chemical_Salinity_ppt',
            'General_Observations'
        ]
        return parameters

    def format_assessment(assessment:Dict[str,Any]) -> List[str]:
        parameters = [
            assessment['investigator1'],
            assessment['investigator2'],
            assessment['collect_date'],
            assessment['collect_time'],
            assessment['assessment_type'],
            assessment['weather_cond'],
            assessment['time_since_last_precip'],
            assessment['water_color'],
            assessment['water_odor'],
            assessment['clarity'],
            assessment['water_movement'],
            assessment['surface_coating'],
            assessment['algae_amount'],
            assessment['algae_type'],
            assessment['aquatic_veg_amount'],
            assessment['aquatic_veg_type'],
            assessment['simple_woody_debris_amt'],
            assessment['simple_woody_debris_type'],
            assessment['simple_tree_canopy'],
            assessment['simple_land_use'],
            assessment['simple_air_temperature'],
            assessment['simple_water_temperature'],
            assessment['simple_nitrate'],
            assessment['simple_phosphate'],
            assessment['simple_ph'],
            assessment['simple_turbidity'],
            assessment['simple_turbidity_reagent_amt'],
            assessment['simple_turbidity_sample_size'],
            assessment['simple_dissolved_oxygen'],
            assessment['simple_salinity'],
            assessment['site_observation'],
        ]
        return parameters

    site = SiteRegistration.objects.get(sampling_feature_code=sampling_feature_code)
    assessments = [models.StreamWatchODM2Adapter.from_action_id(a) for a in actionids.split(',')]

    filename = f'streamwatchdata_{sampling_feature_code}_{datetime.datetime.now().strftime("%Y-%m-%d")}.csv'
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerows(format_metadata(site))
    writer.writerow(format_header())

    for assessment in assessments:
        writer.writerow(format_assessment(assessment.to_dict(True)))

    return response
