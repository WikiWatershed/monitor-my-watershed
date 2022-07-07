from dataloaderinterface.models import SiteRegistration
from django.views.generic.edit import UpdateView, CreateView, DeleteView, FormView, BaseDetailView
from django.views.generic.detail import DetailView
from django.shortcuts import reverse, redirect
from django.http import HttpResponse
from django.http import response
from django.contrib.auth.decorators import login_required

from formtools.wizard.views import SessionWizardView
from streamwatch import forms 

import django

from streamwatch import models

class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls):
        return login_required(super(LoginRequiredMixin, cls).as_view())


class StreamWatchListUpdateView(LoginRequiredMixin, DetailView):
    template_name = 'dataloaderinterface/manage_streamwatch.html'
    model = SiteRegistration
    slug_field = 'sampling_feature_code'
    slug_url_kwarg = 'sampling_feature_code'

    def dispatch(self, request, *args, **kwargs):
        site = SiteRegistration.objects.get(sampling_feature_code=self.kwargs['sampling_feature_code'])
        if request.user.is_authenticated and not request.user.can_administer_site(site):
            raise response.Http404
        return super(StreamWatchListUpdateView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return SiteRegistration.objects.with_leafpacks()

    def get_context_data(self, **kwargs):
        context = super(StreamWatchListUpdateView, self).get_context_data(**kwargs)
        return context

class CATCreateView(SessionWizardView):
    form_list = [
        ('setup',StreamWatchForm), 
        ('conditions',StreamWatchForm2)
        ('setup',forms.SetupForm), 
        ('conditions',forms.ConditionsForm),
    ]
    template_name = 'streamwatch/streamwatch_wizard.html'
    slug_field = 'sampling_feature_code'
    object = None

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        context['sampling_feature_code'] = self.kwargs[self.slug_field]

        if self.steps.current == 'my_step_name':
            context.update({'another_var': True})
        
        setup_data = self.get_cleaned_data_for_step('setup')
        if setup_data:
            if 'chemical' in setup_data['activity_type']:
                self.form_list['cat'] = forms.CATForm
            if 'biological' in setup_data['activity_type']:
                #TODO - PRT these are placeholders from when these forms are implemented
                pass
            if 'bacterial' in setup_data['activity_type']:
                #TODO - PRT these are placeholders from when these forms are implemented
                pass
        return context
       
    def done(self, form_list, **kwargs):
        id = models.sampling_feature_code_to_id(self.sampling_feature_code)
        
        form_data = {'sampling_feature_id':id}
        for form in form_list: form_data = form_data | form.cleaned_data
        adapter = models.StreamWatchODM2Adapter.create_from_dict(form_data)

        #form_data =  form.cleaned_data for form in form_list]
        # save/update 
        return redirect(reverse('streamwatches', kwargs={self.slug_field: self.kwargs[self.slug_field]}))

class CAT_Measurement:
        def __init__(self, name, id,cal_date):
            self.name= name
            self.id=id
            self.cal_date= cal_date
            
class CAT_Parameter:
    def __init__(self, name, measurement,unit):
        self.parName= name
        self.measurement=measurement
        self.unit= unit
    
    
class StreamWatchDetailView(DetailView):
    template_name = 'streamwatch/streamwatch_detail.html'
    slug_field = 'sampling_feature_code'
    context_object_name ='streamwatch'
    #model = LeafPack

    def get_object(self, queryset=None):
        #return LeafPack.objects.get(id=self.kwargs['pk'])
        streamwatch ={}
        streamwatch['sampling_feature_code'] = self.kwargs[self.slug_field]
        streamwatch['investigator1'] ='John Doe'
        streamwatch['investigator2'] ='Jane Doe'
        streamwatch['collect_date']='6/1/2022'
        streamwatch['project_name']='Superman #1'
        streamwatch['reach_length']='2 miles'
        streamwatch['weather_cond']='Cloudy'
        streamwatch['time_since_last_precip']='10 hrs'
        streamwatch['water_color']='Clear'
        streamwatch['water_odor']='Normal'
        
        streamwatch['turbidity_obs']='Clear'
        streamwatch['water_movement']='Swift/Waves'
        streamwatch['aquatic_veg_amount']='Scarce'
        streamwatch['aquatic_veg_type']='Submergent'
        streamwatch['surface_coating']='None'
        streamwatch['algae_amount']='Scarce'
        streamwatch['algae_type']='Filamentous'
        streamwatch['site_observation']='Some comments on and on...'
        
        streamwatch['CAT_measurements']=[]
        
        
        par1 = []
        par1.append(CAT_Parameter("Air temperature", 15, "C"))
        par1.append(CAT_Parameter("Dissolved oxygen", 6.5, "mg/L"))
        par1.append(CAT_Parameter("Phosphorus", 9.5, "ug/L"))
        meas1 = CAT_Measurement("YSI1","4531","06/13/2011")
        meas1.pars = par1
        streamwatch['CAT_measurements'].append(meas1)
        
        par2 = []
        par2.append(CAT_Parameter("Air temperature", 16, "C"))
        par2.append(CAT_Parameter("Dissolved oxygen", 7.5, "mg/L"))
        par2.append(CAT_Parameter("Phosphorus", 6.5, "ug/L"))
        meas2 = CAT_Measurement("YSI2","4555","10/30/2007")
        meas2.pars = par2
        
        streamwatch['CAT_measurements'].append(meas2)
        return streamwatch
        

class StreamWatchDeleteView(LoginRequiredMixin, DeleteView):
    slug_field = 'sampling_feature_code'

    def get_object(self, queryset=None):
        #return LeafPack.objects.get(id=self.kwargs['pk'])
        return {}

    def post(self, request, *args, **kwargs):
        # to do: implement delete current streamWatch assessment
        #leafpack = self.get_object()
        #leafpack.delete()
        return redirect(reverse('site_detail', kwargs={self.slug_field: self.kwargs[self.slug_field]}))

# add a streamwatch meas to CAT assessment

parameter_formset=django.forms.formset_factory(forms.CATParameterForm, extra=4)
class StreamWatchCreateMeasurementView(FormView):
    form_class = forms.CATForm
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

        context['sampling_feature_code'] = self.kwargs[self.slug_field]

        if self.object is None:
            site_registration = SiteRegistration.objects.get(sampling_feature_code=self.kwargs[self.slug_field])
            context['form'] = forms.CATForm(initial={'site_registration': site_registration}, prefix='meas')
            context['parameter_forms'] = parameter_formset(prefix ='para')

        return context
    
    def post(self, request, *args, **kwargs):
            
        # to do: implement save current streamWatch assessment
        
        form = forms.CATForm(request.POST, prefix='meas')
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
    Download handler that uses csv_writer.py to parse out a leaf pack expirement into a csv file.

    :param request: the request object
    :param sampling_feature_code: the first URL parameter
    :param pk: the second URL parameter and id of the leafpack experiement to download 
    """
    filename, content = get_leafpack_csv(sampling_feature_code, pk)

    response = HttpResponse(content, content_type='application/csv')
    response['Content-Disposition'] = 'inline; filename={0}'.format(filename)

    return response


def get_leafpack_csv(sfc, lpid):  # type: (str, int) -> (str, str)
    # leafpack = LeafPack.objects.get(id=lpid)
    # site = SiteRegistration.objects.get(sampling_feature_code=sfc)

    # writer = LeafPackCSVWriter(leafpack, site)
    # writer.write()

    return None #writer.filename(), writer.read()
