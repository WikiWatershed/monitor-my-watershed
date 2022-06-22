# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
from dataloaderinterface.models import SiteRegistration
from django.views.generic.edit import UpdateView, CreateView, DeleteView, FormView, BaseDetailView
from django.views.generic.detail import DetailView
from django.shortcuts import reverse, redirect
from django.http import HttpResponse
from django.core.management import call_command
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required

from formtools.wizard.views import SessionWizardView, WizardView

from .forms import StreamWatchForm, StreamWatchForm2, StreamWatchForm3, StreamWatch_CAT_Sensor_Form, StreamWatch_Sensor_Form, StreamWatch_Sensor_Parameter_Form, formset_factory

class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls):
        return login_required(super(LoginRequiredMixin, cls).as_view())


class xStreamWatchCreateView(FormView):
    """
    Create View
    """
    form_class = StreamWatchForm
    template_name = 'streamwatch/streamwatch_form.html'
    slug_field = 'sampling_feature_code'
    object = None
    
    def get_context_data(self, **kwargs):
            # if 'leafpack_form' is in kwargs, that means self.form_invalid was most likely called due to a failed POST request
        if 'form' in kwargs:
            self.object = kwargs['form'].instance

        context = super(StreamWatchCreateView, self).get_context_data(**kwargs)

        context['sampling_feature_code'] = self.kwargs[self.slug_field]

        if self.object is None:
            site_registration = SiteRegistration.objects.get(sampling_feature_code=self.kwargs[self.slug_field])
            context['form'] = StreamWatchForm(initial={'site_registration': site_registration})

        return context


class StreamWatchCreateView(SessionWizardView):
    """
    Create View
    """
    #form_class = StreamWatchForm
    form_list = [StreamWatchForm, StreamWatchForm2]
    template_name = 'streamwatch/streamwatch_wizard.html'
    #template_name = 'streamwatch/example.html'
    slug_field = 'sampling_feature_code'
    object = None
    
    # def get(self, request, *args, **kwargs):
    #     try:
    #         return self.render(self.get_form())
    #     except KeyError:
    #         return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
            # if 'leafpack_form' is in kwargs, that means self.form_invalid was most likely called due to a failed POST request
        # if 'form' in kwargs:
        #     self.object = kwargs['form'].instance

        context = super(StreamWatchCreateView, self).get_context_data(**kwargs)

        context['sampling_feature_code'] = self.kwargs[self.slug_field]

        # if self.object is None:
        #     site_registration = SiteRegistration.objects.get(sampling_feature_code=self.kwargs[self.slug_field])
        #     context['form'] = StreamWatchForm(initial={'site_registration': site_registration})

        return context
    
    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        context['sampling_feature_code'] = self.kwargs[self.slug_field]

        if self.steps.current == 'my_step_name':
            context.update({'another_var': True})
        
        start_form_data = self.get_cleaned_data_for_step('0')
        if start_form_data:
            if 'chemical' in start_form_data['activity_type']:
                context['CAT']= True
            else:
                context['CAT']= False
                    
        return context
       
    
    # def get_form_step_data(self, form):
    #     if self.steps.current == '0':
    #         self.activity_type = form.cleaned_data['activity_type'];
    #     return form.data
    
class StreamWatchDeleteView(LoginRequiredMixin, DeleteView):
    """
    Delete view
    """
    slug_field = 'sampling_feature_code'

    def get_object(self, queryset=None):
        #return LeafPack.objects.get(id=self.kwargs['pk'])
        return None

    def post(self, request, *args, **kwargs):
        
        # to do: implement delete current streamWatch assessment
        
        #leafpack = self.get_object()
        #leafpack.delete()
        return redirect(reverse('site_detail', kwargs={self.slug_field: self.kwargs[self.slug_field]}))

# add a streamwatch sensor to CAT assessment

parameter_formset=formset_factory(StreamWatch_Sensor_Parameter_Form, extra=1)
class StreamWatchCreateSensorView(FormView):
    """
    Create View
    """
    form_class = StreamWatch_Sensor_Form
    template_name = 'streamwatch/streamwatch_sensor.html'
    slug_field = 'sampling_feature_code'
    object = None
    
    def get_context_data(self, **kwargs):
            # if 'leafpack_form' is in kwargs, that means self.form_invalid was most likely called due to a failed POST request
        if 'form' in kwargs:
            self.object = kwargs['form']

        context = super(StreamWatchCreateSensorView, self).get_context_data(**kwargs)

        context['sampling_feature_code'] = self.kwargs[self.slug_field]

        if self.object is None:
            site_registration = SiteRegistration.objects.get(sampling_feature_code=self.kwargs[self.slug_field])
            context['form'] = StreamWatch_Sensor_Form(initial={'site_registration': site_registration}, prefix='sensor')
            context['parameter_formset'] = parameter_formset(prefix ='para')

        return context
    
    def post(self, request, *args, **kwargs):
            
        # to do: implement save current streamWatch assessment
        
        sensor_form = StreamWatch_Sensor_Form(request.POST, prefix='sensor')
        para_forms = parameter_formset(request.POST, prefix='para')
        if sensor_form.is_valid() and para_forms.is_valid():
            # process the data …
            #leafpack = self.get_object()
            #leafpack.save()
            return redirect(reverse('streamwatches', kwargs={self.slug_field: self.kwargs[self.slug_field]}))