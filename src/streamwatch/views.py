import csv
import os
import datetime
from typing import List, TextIO, Dict, Any

import django
from django.core.files.storage import FileSystemStorage
from django.shortcuts import reverse, redirect
from django.http import HttpResponse
from django.http import response
from django.conf import settings

from django.contrib.auth.decorators import login_required
from formtools.wizard.views import SessionWizardView

from dataloaderinterface.models import SiteRegistration
from streamwatch import models
from streamwatch import forms

PHOTO_DIRECTORY = os.path.join(settings.MEDIA_ROOT, "streamwatch_site_photos")


class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls):
        return login_required(super(LoginRequiredMixin, cls).as_view())


class ListUpdateView(LoginRequiredMixin, django.views.generic.detail.DetailView):
    template_name = "dataloaderinterface/manage_streamwatch.html"
    model = SiteRegistration
    slug_field = "sampling_feature_code"
    slug_url_kwarg = "sampling_feature_code"

    def dispatch(self, request, *args, **kwargs) -> HttpResponse:
        site = SiteRegistration.objects.get(
            sampling_feature_code=self.kwargs[self.slug_field]
        )
        if request.user.is_authenticated and not request.user.can_administer_site(
            site.sampling_feature_id
        ):
            raise response.Http404
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        sampling_feature_code = self.kwargs[self.slug_field]
        assessments = models.samplingfeature_assessments(sampling_feature_code)
        context["streamwatchsurveys"] = assessments
        return context


def condition_cat(wizard):
    setup_data = wizard.get_cleaned_data_for_step("setup")
    if setup_data is not None:
        return "chemical" in setup_data["assessment_type"]
    return True


# TODO - reenable conditional if different assessment types are needed
def condition_school(wizard):
    setup_data = wizard.get_cleaned_data_for_step("setup")
    # uncomment to enable assessment type selection again
    # if setup_data is not None:
    #    return 'school' in setup_data['assessment_type']
    return True


class CreateView(SessionWizardView):
    form_list = [
        ("setup", forms.SetupForm),
        ("conditions", forms.VisualAssessmentForm),
        ("simplehabitat", forms.SimpleHabitatAssessmentForm),
        ("simplewaterquality", forms.SimpleWaterQualityForm),
        ("macros", forms.MacroInvertebrateForm),
        ("photos", forms.SitePhotosForm),
    ]
    condition_dict = {
        "simplewaterquality": condition_school,
        "simplehabitat": condition_school,
    }
    file_storage = FileSystemStorage(location=PHOTO_DIRECTORY)
    template_name = "streamwatch/streamwatch_wizard.html"
    slug_field = "sampling_feature_code"

    def get_context_data(self, form: django.forms.Form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        context[self.slug_field] = self.kwargs[self.slug_field]
        return context

    def done(self, form_list: List[django.forms.Form], **kwargs):
        sampling_feature_id = models.sampling_feature_code_to_id(
            self.kwargs[self.slug_field]
        )

        form_data = {"sampling_feature_id": sampling_feature_id, "cat_methods": []}
        for form in form_list:
            if isinstance(form, forms.WaterQualityForm):
                form_data["cat_methods"].append(form.clean_data())
                continue
            form_data.update(form.cleaned_data)
        adapter = models.StreamWatchODM2Adapter.from_dict(form_data)

        return redirect(
            reverse(
                "streamwatches", kwargs={self.slug_field: self.kwargs[self.slug_field]}
            )
        )


class UpdateView(CreateView):
    PRIMARY_KEY_FIELD = "action_id"

    def get(self, request, *args, **kwargs):
        if self.PRIMARY_KEY_FIELD in kwargs.keys():
            action_id = int(kwargs[self.PRIMARY_KEY_FIELD])
            adapter = models.StreamWatchODM2Adapter.from_action_id(action_id)
            form_data = adapter.to_dict()
            for form_name in self.form_list:
                self.initial_dict[form_name] = form_data

        return super().get(request, *args, **kwargs)

    def get_context_data(self, form: django.forms.Form, **kwargs):
        context_data = super().get_context_data(form, **kwargs)
        if self.PRIMARY_KEY_FIELD in self.kwargs:
            context_data[self.PRIMARY_KEY_FIELD] = self.kwargs[self.PRIMARY_KEY_FIELD]
        return context_data

    def done(self, form_list: List[django.forms.Form], **kwargs):
        sampling_feature_id = models.sampling_feature_code_to_id(
            self.kwargs[self.slug_field]
        )
        form_data = {"sampling_feature_id": sampling_feature_id, "cat_methods": []}
        for form in form_list:
            if isinstance(form, forms.WaterQualityForm):
                form_data["cat_methods"].append(form.clean_data())
                continue
            form_data.update(form.cleaned_data)

        action_id = int(self.kwargs[self.PRIMARY_KEY_FIELD])
        adapter = models.StreamWatchODM2Adapter.from_action_id(action_id)
        adapter.update_from_dict(form_data)

        return redirect(
            reverse(
                "streamwatches", kwargs={self.slug_field: self.kwargs[self.slug_field]}
            )
        )


class DetailView(django.views.generic.detail.DetailView):
    template_name = "streamwatch/streamwatch_detail.html"
    slug_field = "sampling_feature_code"
    context_object_name = "streamwatch"

    def get_object(self, queryset=None):
        action_id = int(self.kwargs["pk"])
        adapter = models.StreamWatchODM2Adapter.from_action_id(action_id)
        data = adapter.to_dict(string_format=True)

        # add in list of macro field
        data["macro_fields"] = forms.MacroInvertebrateForm.declared_fields
        return data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        registration = SiteRegistration.objects.get(
            sampling_feature_code=self.kwargs[self.slug_field]
        )
        user = self.request.user
        context[
            "can_administer_site"
        ] = user.is_authenticated and user.can_administer_site(
            registration.sampling_feature_id
        )
        context["is_site_owner"] = user.id == registration.django_user
        context["sampling_feature_code"] = self.kwargs[self.slug_field]
        context["action_id"] = int(self.kwargs["pk"])
        return context


class DeleteView(LoginRequiredMixin, django.views.generic.edit.DeleteView):
    slug_field = "sampling_feature_code"

    def post(self, request, *args, **kwargs):
        # if not passed via post body, check query parameters
        feature_action_id = request.POST.get("id", kwargs["id"])
        models.delete_streamwatch_assessment(feature_action_id)
        # if specified via post parameter we want to issue success response
        if "id" in request.POST:
            return HttpResponse("Assessment deleted successfully", status=200)
        return redirect(
            reverse(
                "streamwatches",
                kwargs={self.slug_field: self.kwargs[self.slug_field]},
            )
        )


parameter_formset = django.forms.formset_factory(
    forms.WaterQualityParametersForm, extra=4
)


class StreamWatchCreateMeasurementView(django.views.generic.edit.FormView):
    form_class = forms.WaterQualityForm
    template_name = "streamwatch/streamwatch_sensor.html"
    slug_field = "sampling_feature_code"
    object = None

    def form_invalid(self, measurement_form, parameter_forms):
        context = self.get_context_data(
            form=measurement_form, parameter_forms=parameter_forms
        )
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        # if 'leafpack_form' is in kwargs, that means self.form_invalid was most likely called due to a failed POST request
        if "form" in kwargs:
            self.object = kwargs["form"]

        context = super(StreamWatchCreateMeasurementView, self).get_context_data(
            **kwargs
        )

        context[self.slug_field] = self.kwargs[self.slug_field]

        if self.object is None:
            site_registration = SiteRegistration.objects.get(
                sampling_feature_code=self.kwargs[self.slug_field]
            )
            context["form"] = forms.WaterQualityForm(
                initial={"site_registration": site_registration}, prefix="meas"
            )
            context["parameter_forms"] = parameter_formset(prefix="para")

        return context

    def post(self, request, *args, **kwargs):
        # to do: implement save current streamWatch assessment

        form = forms.WaterQualityForm(request.POST, prefix="meas")
        parameter_forms = parameter_formset(request.POST, prefix="para")
        if form.is_valid() and parameter_forms.is_valid():
            # process the data …
            # leafpack = self.get_object()
            # leafpack.save()

            return redirect(
                reverse(
                    "streamwatches",
                    kwargs={self.slug_field: self.kwargs[self.slug_field]},
                )
            )
        else:
            return self.form_invalid(form, parameter_forms)


def csv_export(request, sampling_feature_code: str, actionids: str):
    """
    Download handler that uses csv_writer.py to parse out a StreamWatch assessment into a csv file.

    :param request: the request object
    :param sampling_feature_code: the first URL parameter
    :param pk: the second URL parameter and id of the leafpack experiement to download
    """

    def format_metadata(site: SiteRegistration) -> List[List[str]]:
        result = [
            [f"# Site Information"],
            [f"# ----------------"],
            [f"SiteCode: {site.sampling_feature_code}"],
            [f"SiteName: {site.sampling_feature_name}"],
            [f"SiteDescription: {site.sampling_feature.sampling_feature_description}"],
            [f"Latitude: {site.latitude}"],
            [f"Longitude: {site.longitude}"],
            [f"Elevation: {site.longitude}"],
            [f"VerticalDatum: {site.sampling_feature.elevation_datum}"],
            [f"SiteType: {site.site_type}"],
            [f"SiteNotes: {site.site_notes}"],
            [f"# "],
        ]
        return result

    def format_header() -> List[str]:
        parameters = [
            "Investigator_1",
            "Investigator_2",
            "Assessment_Date",
            "Assessment_Time",
            "Assessment_Types",
            "Visual_Weather",
            "Visual_Time_Since_Rainfall",
            "Visual_Water_Color",
            "Visual_Water_Odor",
            "Visual_Water_Odor_Other",
            "Visual_Turbidity",
            "Visual_Water_Movement",
            "Visual_Surface_Coating",
            "Visual_Aquatic_Vegetation_Amount",
            "Visual_Aquatic_Vegetation_Type",
            "Visual_Algae_Amount",
            "Visual_Algae_Type",
            "Habitat_Woody_Debris_Amount",
            "Habitat_Woody_Debris_Type",
            "Habitat_Tree_Canopy",
            "Habitat_Land_Use",
            "Chemical_Air_Temperature_degC",
            "Chemical_Water_Temperature_degC",
            "Chemical_Nitrate_Nitrogen_ppm",
            "Chemical_Phosphates_ppm",
            "Chemical_pH",
            "Chemical_Turbidity_JTU",
            "Chemical_Dissolved_Oxygen_ppm",
            "Chemical_Salinity_ppt",
            "General_Observations",
        ]
        return parameters

    def format_assessment(assessment: Dict[str, Any]) -> List[str]:
        parameters = [
            assessment["investigator1"],
            assessment["investigator2"],
            assessment["collect_date"],
            assessment["collect_time"],
            assessment["assessment_type"],
            assessment["weather_cond"] if "weather_cond" in assessment else None,
            assessment["time_since_last_precip"]
            if "time_since_last_precip" in assessment
            else None,
            assessment["water_color"] if "water_color" in assessment else None,
            assessment["water_odor"] if "water_odor" in assessment else None,
            assessment["water_odor_other"]
            if "water_odor_other" in assessment
            else None,
            assessment["clarity"] if "clarity" in assessment else None,
            assessment["water_movement"] if "water_movement" in assessment else None,
            assessment["surface_coating"] if "surface_coating" in assessment else None,
            assessment["algae_amount"] if "algae_amount" in assessment else None,
            assessment["algae_type"] if "algae_type" in assessment else None,
            assessment["aquatic_veg_amount"]
            if "aquatic_veg_amount" in assessment
            else None,
            assessment["aquatic_veg_type"]
            if "aquatic_veg_type" in assessment
            else None,
            assessment["simple_woody_debris_amt"]
            if "simple_woody_debris_amt" in assessment
            else None,
            assessment["simple_woody_debris_type"]
            if "simple_woody_debris_type" in assessment
            else None,
            assessment["simple_tree_canopy"]
            if "simple_tree_canopy" in assessment
            else None,
            assessment["simple_land_use"] if "simple_land_use" in assessment else None,
            assessment["simple_air_temperature"]
            if "simple_air_temperature" in assessment
            else None,
            assessment["simple_water_temperature"]
            if "simple_water_temperature" in assessment
            else None,
            assessment["simple_nitrate"] if "simple_nitrate" in assessment else None,
            assessment["simple_phosphate"]
            if "simple_phosphate" in assessment
            else None,
            assessment["simple_ph"] if "simple_ph" in assessment else None,
            assessment["simple_turbidity"]
            if "simple_turbidity" in assessment
            else None,
            assessment["simple_turbidity_reagent_amt"]
            if "simple_turbidity_reagent_amt" in assessment
            else None,
            assessment["simple_turbidity_sample_size"]
            if "simple_turbidity_sample_size" in assessment
            else None,
            assessment["simple_dissolved_oxygen"]
            if "simple_dissolved_oxygen" in assessment
            else None,
            assessment["simple_salinity"] if "simple_salinity" in assessment else None,
            assessment["site_observation"]
            if "site_observation" in assessment
            else None,
        ]
        return parameters

    site = SiteRegistration.objects.get(sampling_feature_code=sampling_feature_code)
    assessments = [
        models.StreamWatchODM2Adapter.from_action_id(a) for a in actionids.split(",")
    ]

    filename = f'streamwatchdata_{sampling_feature_code}_{datetime.datetime.now().strftime("%Y-%m-%d")}.csv'
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerows(format_metadata(site))
    writer.writerow(format_header())

    for assessment in assessments:
        writer.writerow(format_assessment(assessment.to_dict(True)))

    return response
