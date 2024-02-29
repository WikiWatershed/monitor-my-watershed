# -*- coding: utf-8 -*-
import logging
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from django.urls import reverse, reverse_lazy
from django.core.exceptions import ObjectDoesNotExist
from django.http.response import HttpResponseRedirect, Http404
from django.shortcuts import redirect
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import UpdateView, CreateView, DeleteView, ModelFormMixin
from django.views.generic.list import ListView

from dataloader.models import ElevationDatum, SiteType, Organization
from dataloaderinterface.models import SiteRegistration
from dataloaderinterface.forms import (
    SiteAlertForm,
    SiteRegistrationForm,
    SiteSensorForm,
    SensorDataForm,
)
from hydroshare.models import HydroShareResource, HydroShareAccount
from leafpack.models import LeafPack

from django.views.decorators.csrf import csrf_exempt
import dataloaderinterface.ajax as ajax
from django.core.handlers.wsgi import WSGIRequest

import json
from django.http import HttpResponse, JsonResponse
from typing import Any, Dict, Union
import streamwatch

import accounts

from odm2 import odm2datamodels
from sqlalchemy import text

class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls):
        return login_required(super(LoginRequiredMixin, cls).as_view())


class HomeView(TemplateView):
    template_name = "dataloaderinterface/home.html"


class TermsOfUseView(TemplateView):
    template_name = "dataloaderinterface/terms_of_use.html"


class DMCAView(TemplateView):
    template_name = "dataloaderinterface/dmca.html"


class PrivacyView(TemplateView):
    template_name = "dataloaderinterface/privacy.html"


class CookiePolicyView(TemplateView):
    template_name = "dataloaderinterface/cookie_policy.html"


class SubscriptionsView(TemplateView):
    template_name = "dataloaderinterface/subscriptions.html"


class SubscriptionsFAQView(TemplateView):
    template_name = "dataloaderinterface/subscriptions_faq.html"


class SitesListView(LoginRequiredMixin, ListView):
    model = SiteRegistration
    context_object_name = "sites"
    template_name = "dataloaderinterface/my-sites.html"

    def get_queryset(self):
        return (
            super(SitesListView, self)
            .get_queryset()
            .with_sensors()
            .with_latest_measurement_id()
            .deployed_by(organization_ids=self.request.user.organization_id)
        )

    def get_context_data(self, **kwargs):
        context = super(SitesListView, self).get_context_data()
        context["followed_sites"] = (
            super(SitesListView, self)
            .get_queryset()
            .with_sensors()
            .with_latest_measurement_id()
            .followed_by(user_id=self.request.user.id)
        )
        #we want to preorder affiliations 
        affiliated_orgs = {}
        for affiliation in self.request.user.affiliation:
            org = affiliation.organization
            if org.organization_type.name == "Individual":
                affiliated_orgs[' '] = org
                continue
            affiliated_orgs[org.organization_name] = org
        context["organizations"] = dict(sorted(affiliated_orgs.items())).values()
        
        organization_site_counts = {}
        for site in context['sites']:
            try:
                organization_site_counts[site.organization_id] += 1
            except KeyError:
                organization_site_counts[site.organization_id] = 1
        context['organization_site_counts'] = organization_site_counts        

        return context


class StatusListView(ListView):
    model = SiteRegistration
    context_object_name = "sites"
    template_name = "dataloaderinterface/status.html"

    def get_queryset(self):
        return (
            super(StatusListView, self)
            .get_queryset()
            .with_status_sensors()
            .deployed_by(self.request.user.id)
            .with_latest_measurement_id()
            .order_by("sampling_feature_code")
        )

    def get_context_data(self, **kwargs):
        context = super(StatusListView, self).get_context_data(**kwargs)
        context["followed_sites"] = (
            super(StatusListView, self)
            .get_queryset()
            .with_status_sensors()
            .followed_by(user_id=self.request.user.id)
            .with_latest_measurement_id()
            .order_by("sampling_feature_code")
        )
        return context


class BrowseSitesListView(ListView):
    model = SiteRegistration
    context_object_name = "sites"
    template_name = "dataloaderinterface/browse-sites.html"
    __VALID_FILTERS = ("dataTypes", "organizations", "siteTypes")

    def get_context_data(self, request, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)

        # populate preselected filters, passed in  querystring/kwargs
        filters = {}
        for f in self.__VALID_FILTERS:
            val = request.GET[f].split(",") if f in request.GET else None
            filters[f] = val
        context["filters"] = json.dumps(filters)

        #pull data from database
        context["data"] = self.get_site_data()

        #set ownership status
        organization_ids = request.user.organization_id 
        for d in context["data"]:
            d["ownership_status"] = 'affiliated' if d["organization_id"] in organization_ids else ''

        return context

    def get(self, request, *args, **kwargs) -> HttpResponse:
        self.object_list = []
        context = self.get_context_data(request)
        return self.render_to_response(context)

    #TODO: move to crud endpoint that uses SQLAlchemy models
    def get_site_data(self):
        """Method to fetch site data required for template"""
        sql = '''
            WITH last_measurement AS (
                SELECT 
                    ss."RegistrationID" 
                    ,MAX(sm.value_datetime + sm.value_datetime_utc_offset) AS latestmeasurement
                    ,MAX(sm.value_datetime) AS latestmeasurement_utc
                    ,MAX(sm.value_datetime_utc_offset) AS latestmeasurement_utc_offset
                FROM dataloaderinterface_sensormeasurement AS sm
                JOIN dataloaderinterface_sitesensor AS ss 
                    ON sm.sensor_id = ss.id 
                GROUP BY (ss."RegistrationID")
            )
            ,leafpack AS (
                SELECT site_registration_id, COUNT(id) AS leafpack_count
                FROM leafpack
                GROUP BY "site_registration_id"
            ) 
            SELECT 
                sr."SamplingFeatureID" AS sampling_feature_id
                ,sr."SamplingFeatureCode" AS sampling_feature_code
                ,org.organizationid AS organization_id
                ,org.organizationtypecv AS organization_type
                ,org.organizationcode AS organization_code
                ,org.organizationname AS organization_name  
                ,sr."StreamName" AS stream_name
                ,sr."MajorWatershed" AS major_watershed
                ,sr."SubBasin" AS sub_basin
                ,sr."ClosestTown" AS closest_town
                ,sr."SiteNotes" AS site_notes
                ,sr."SiteType" AS site_type
                ,sr."SamplingFeatureName" AS sampling_feature_name
                ,sr."Latitude" AS latitude
                ,sr."Longitude" AS longitude
                ,sr."Elevation" AS elevation
                ,lm.latestmeasurement_utc AS latest_measurement_utc
                ,lm.latestmeasurement_utc_offset AS latest_measurement_utcoffset
                ,lm.latestmeasurement AS latest_measurement
                ,lp.leafpack_count AS leafpack_count
                ,sr.streamwatch_assessments AS streamwatch_count

            FROM public.dataloaderinterface_siteregistration AS sr
            JOIN odm2.organizations AS org ON sr."OrganizationID" = org.organizationid
            LEFT JOIN last_measurement AS lm ON lm."RegistrationID" = sr."RegistrationID"
            LEFT JOIN leafpack AS lp ON lp.site_registration_id = sr."RegistrationID"
        '''

        with odm2datamodels.odm2_engine.session_maker() as session:
            result = session.execute(text(sql)).mappings().all()

        return [dict(d) for d in result]



class SiteDetailView(DetailView):
    model = SiteRegistration
    context_object_name = "site"
    slug_field = "sampling_feature_code"
    slug_url_kwarg = "sampling_feature_code"
    template_name = "dataloaderinterface/site_details.html"

    def get_queryset(self):
        return (
            super(SiteDetailView, self)
            .get_queryset()
            .with_sensors()
            .with_sensors_last_measurement()
        )

    def get_context_data(self, **kwargs):
        context = super(SiteDetailView, self).get_context_data(**kwargs)
        context["data_upload_form"] = SensorDataForm()
        context["is_followed"] = self.object.followed_by.filter(
            accountid=self.request.user.id
        ).exists()
        context["can_administer_site"] = self.request.user.can_administer_site(
            self.object.sampling_feature_id
        )
        context["is_site_owner"] = self.request.user.owns_site(
            self.object.sampling_feature_id
        )

        context["leafpacks"] = LeafPack.objects.filter(
            site_registration=context["site"].pk
        ).order_by("-placement_date")
        context["streamwatch"] = streamwatch.models.samplingfeature_assessments(
            self.kwargs[self.slug_field]
        )
        if context["streamwatch"]:
            context["streamwatch_actionids"] = ",".join(
                [str(a["actionid"]) for a in context["streamwatch"]]
            )

        try:
            context["hydroshare_account"] = self.request.user.hydroshare_account
        except AttributeError:
            pass

        try:
            resources = HydroShareResource.objects.filter(
                site_registration=context["site"].pk
            )
            visible_resources = [res for res in resources if res.visible]
            context["resource_is_connected"] = len(visible_resources) > 0
        except ObjectDoesNotExist:
            pass

        return context


class SensorListUpdateView(LoginRequiredMixin, DetailView):
    template_name = "dataloaderinterface/manage_sensors.html"
    model = SiteRegistration
    slug_field = "sampling_feature_code"
    slug_url_kwarg = "sampling_feature_code"
    context_object_name = "site_registration"

    def dispatch(self, request, *args, **kwargs):
        site = SiteRegistration.objects.get(
            sampling_feature_code=self.kwargs["sampling_feature_code"]
        )
        if request.user.is_authenticated and not request.user.can_administer_site(
            site.sampling_feature_id
        ):
            raise Http404
        return super(SensorListUpdateView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return super(SensorListUpdateView, self).get_queryset().with_sensors()

    def get_context_data(self, **kwargs):
        context = super(SensorListUpdateView, self).get_context_data(**kwargs)
        context["sensor_form"] = SiteSensorForm(
            initial={"registration": self.object.registration_id}
        )

        return context


class LeafPackListUpdateView(LoginRequiredMixin, DetailView):
    template_name = "dataloaderinterface/manage_leafpack.html"
    model = SiteRegistration
    slug_field = "sampling_feature_code"
    slug_url_kwarg = "sampling_feature_code"

    def dispatch(self, request, *args, **kwargs):
        site = SiteRegistration.objects.get(
            sampling_feature_code=self.kwargs["sampling_feature_code"]
        )
        if request.user.is_authenticated and not request.user.can_administer_site(
            site.sampling_feature_id
        ):
            raise Http404
        return super(LeafPackListUpdateView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return SiteRegistration.objects.with_leafpacks()

    def get_context_data(self, **kwargs):
        context = super(LeafPackListUpdateView, self).get_context_data(**kwargs)
        return context


class SiteDeleteView(LoginRequiredMixin, DeleteView):
    model = SiteRegistration
    slug_field = "sampling_feature_code"
    slug_url_kwarg = "sampling_feature_code"
    success_url = reverse_lazy("sites_list")

    def dispatch(self, request, *args, **kwargs):
        registration = self.get_object()
        if request.user.is_authenticated and not request.user.can_administer_site(
            registration.sampling_feature_id
        ):
            raise Http404
        return super(SiteDeleteView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return redirect(
            reverse(
                "site_detail",
                kwargs={
                    "sampling_feature_code": self.get_object().sampling_feature_code
                },
            )
        )

    def post(self, request, *args, **kwargs):
        site_registration = self.get_object()
        site_registration.delete()

        messages.success(request, "The site has been deleted successfully.")
        return HttpResponseRedirect(self.success_url)


class SiteUpdateView(LoginRequiredMixin, UpdateView):
    template_name = "dataloaderinterface/site_registration_update.html"
    slug_url_kwarg = "sampling_feature_code"
    slug_field = "sampling_feature_code"
    form_class = SiteRegistrationForm
    model = SiteRegistration
    object = None

    def dispatch(self, request, *args, **kwargs):
        registration = self.get_object()
        if request.user.is_authenticated and not request.user.can_administer_site(
            registration.sampling_feature_id
        ):
            raise Http404

        return super(SiteUpdateView, self).dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy(
            "site_detail",
            kwargs={"sampling_feature_code": self.object.sampling_feature_code},
        )

    def get_form(self, form_class=None):
        data = self.request.POST or None
        site_registration = self.get_object()
        
        form = self.get_form_class()(data=data, instance=site_registration)
        
        #choices should be a list of tuples with org and org name
        #for general user, we need to filter to only the organizations affiliated with the account
        user = self.request.user
        organization_ids = [a.organization.organization_id for a in user.affiliation]
        #for staff/admins if users is site admin they should see all organizations 
        if not user.is_staff:
            organization_ids = None

        choices = []
        from odm2.crud.organizations import read_organization_names 
        from odm2 import create_session
        session = create_session()
        organizations = read_organization_names(session, organization_ids)

        #process organization records into a displayable name
        for org in organizations:
            display_name = org.organizationname
            #if this is an individual account we will want to display their name instead
            if org.organizationtypecv == "Individual":
                prefix = '(Individual - Myself)' if org.accountid == user.id else '(Individual)'
                display_name = f'{prefix} {org.accountfirstname} {org.accountlastname}'
            choices.append((org.organizationid,display_name))
        form.fields["organization_id"].choices = choices
        return form
        

    def get_queryset(self):
        return super(SiteUpdateView, self).get_queryset().with_sensors()

    def get_hydroshare_accounts(self):
        try:
            return HydroShareAccount.objects.filter(user=self.request.user.id)
        except ObjectDoesNotExist:
            return []

    def get_context_data(self, **kwargs):
        data = self.request.POST or {}
        context = super(SiteUpdateView, self).get_context_data()

        account = accounts.models.Account.objects.get(pk=self.request.user.user_id)
        site_alert = account.site_alerts.filter(
            site_registration__sampling_feature_code=self.get_object().sampling_feature_code
        ).first()

        alert_data = (
            {
                "notify": True,
                "hours_threshold": int(
                    site_alert.hours_threshold.total_seconds() / 3600
                ),
            }
            if site_alert
            else {}
        )

        # maybe just access site.leafpacks in the template? Naw.
        context["leafpacks"] = LeafPack.objects.filter(
            site_registration=self.get_object()
        )
        context["sensor_form"] = SiteSensorForm(
            initial={"registration": self.get_object().registration_id}
        )
        context["email_alert_form"] = SiteAlertForm(data=alert_data)
        context["zoom_level"] = data["zoom-level"] if "zoom-level" in data else None

        return context

    def post(self, request, *args, **kwargs):
        site_registration = self.get_object()
        form = self.get_form()
        notify_form = SiteAlertForm(request.POST)

        if form.is_valid() and notify_form.is_valid():
            form.instance.organization_id = (
                form.cleaned_data["organization_id"]
            )

            account = accounts.models.Account.objects.get(pk=self.request.user.user_id)
            site_alert = account.site_alerts.filter(
                site_registration=site_registration
            ).first()

            if notify_form.cleaned_data["notify"] and site_alert:
                site_alert.hours_threshold = timedelta(
                    hours=int(notify_form.data["hours_threshold"])
                )
                site_alert.save()

            elif notify_form.cleaned_data["notify"] and not site_alert:
                account.site_alerts.create(
                    site_registration=site_registration,
                    hours_threshold=timedelta(
                        hours=int(notify_form.data["hours_threshold"])
                    ),
                )

            elif not notify_form.cleaned_data["notify"] and site_alert:
                site_alert.delete()

            messages.success(request, "The site has been updated successfully.")
            return self.form_valid(form)
        else:
            messages.error(
                request,
                "There are still some required fields that need to be filled out!",
            )
            return self.form_invalid(form)


class SiteRegistrationView(LoginRequiredMixin, CreateView):
    template_name = "dataloaderinterface/site_registration.html"
    form_class = SiteRegistrationForm
    model = SiteRegistration
    object = None

    def get_success_url(self):
        return reverse_lazy(
            "site_detail",
            kwargs={"sampling_feature_code": self.object.sampling_feature_code},
        )

    @staticmethod
    def get_default_data():
        data = {
            "elevation_datum": ElevationDatum.objects.filter(pk="MSL").first(),
            "site_type": SiteType.objects.filter(pk="Stream").first(),
        }
        return data

    def get_form(self, form_class=None):
        data = self.request.POST or None
        form = self.get_form_class()(initial=self.get_default_data(), data=data)
        
        #set list of affiliation to only those of the user
        choices = []
        for a in self.request.user.affiliation:
            choices.append((a.organization.organization_id,a.organization.display_name))
        form.fields["organization_id"].choices = choices
        
        return form

    def get_context_data(self, **kwargs):
        context = super(SiteRegistrationView, self).get_context_data()
        data = self.request.POST or {}
        context["email_alert_form"] = SiteAlertForm(data)
        context["zoom_level"] = data["zoom-level"] if "zoom-level" in data else None
        return context

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        notify_form = SiteAlertForm(request.POST)

        if form.is_valid() and notify_form.is_valid():
            form.instance.organization_id = (
                form.cleaned_data["organization_id"] or request.user.organization_id
            )
            form.instance.user = request.user
            form.instance.save()
            self.object = form.save()

            if notify_form.cleaned_data["notify"]:
                account = accounts.models.Account.objects.get(pk=request.user.user_id)
                account.site_alerts.create(
                    site_registration=form.instance,
                    hours_threshold=timedelta(
                        hours=int(notify_form.data["hours_threshold"])
                    ),
                )
            return super(ModelFormMixin, self).form_valid(form)
        else:
            messages.error(
                request,
                "There are still some required fields that need to be filled out!",
            )
            return self.form_invalid(form)


@csrf_exempt
def ajax_router(request: WSGIRequest) -> Union[JsonResponse, HttpResponse]:
    request_data = json.loads(request.POST.get("request_data"))
    try:
        method = getattr(ajax, request_data["method"])
        response = method(request_data)
        return JsonResponse(response, safe=False)
    except AttributeError as e:  # Invalid method specified
        return HttpResponse(status=405)
