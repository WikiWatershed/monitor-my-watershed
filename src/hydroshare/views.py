# -*- coding: utf-8 -*-
import json
import requests
import logging
from oauthlib.oauth2.rfc6749.errors import TokenExpiredError

from django.conf import settings
from django.utils.safestring import mark_safe

from dataloaderservices.views import CSVDataApi

from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.http.response import HttpResponse, JsonResponse, HttpResponseServerError
from django.shortcuts import redirect
from django.views.generic.base import TemplateView
from django.views.generic.edit import UpdateView, DeleteView

from hydroshare.forms import HydroShareSettingsForm, HydroShareResourceDeleteForm
from dataloaderinterface.models import SiteRegistration, SiteSensor
from hydroshare.models import HydroShareAccount, HydroShareResource, OAuthToken
from hydroshare_util import HydroShareNotFound, HydroShareHTTPException
from hydroshare_util.adapter import HydroShareAdapter
from hydroshare_util.auth import AuthUtil
from hydroshare_util.resource import Resource
from hydroshare_util.coverage import PointCoverage

from leafpack.views import get_leafpack_csv
from leafpack.models import LeafPack


class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls):
        return login_required(super(LoginRequiredMixin, cls).as_view())


class HydroShareResourceViewMixin:
    def __init__(self):
        self.request = None

    def get_hs_resource(self, resource):  # type: (HydroShareResource) -> Resource
        """ Creates a 'hydroshare_util.Resource' object """
        account = self.request.user.hydroshare_account
        token_json = account.get_token()
        auth_util = AuthUtil.authorize(token=token_json)

        # if the oauth access_token expires in less than a week, refresh the token
        seconds_in_week = 60*60*24*7
        if token_json.get('expires_in', seconds_in_week) < seconds_in_week:
            try:
                auth_util.refresh_token()
                account.update_token(auth_util.get_token())
            except Exception as e:
                print(e)

        hs_resource = Resource(auth_util.get_client())
        hs_resource.resource_id = resource.ext_id
        return hs_resource


class HydroShareResourceBaseView(UpdateView):
    slug_field = 'sampling_feature_code'

    def form_invalid(self, form):
        response = super(HydroShareResourceBaseView, self).form_invalid(form)
        if self.request.is_ajax():
            return JsonResponse(form.errors, status=400)
        else:
            return response

    def get_object(self, queryset=None, **kwargs):
        site = SiteRegistration.objects.get(sampling_feature_code=self.kwargs[self.slug_field])
        resource = None

        try:
            # Filter through resources that are visible; there should only be one, so pick the first
            resource = HydroShareResource.objects.filter(site_registration=site.registration_id, visible=True).first()
        except ObjectDoesNotExist:
            pass
        return resource

    def get_context_data(self, **kwargs):
        context = super(HydroShareResourceBaseView, self).get_context_data(**kwargs)
        context['date_format'] = settings.DATETIME_FORMAT
        return context

    def upload_hydroshare_files(self, resource):  # type: (Resource) -> None

        hydroshare_resource = self.object or self.get_object()
        site = SiteRegistration.objects.get(hydroshare_resource=hydroshare_resource)
        # Grab files for uploading to hydroshare
        file_uploads = []

        # if 'TS' is a keyword, add sensor data to file_uploads
        if 'TS' in hydroshare_resource.data_types:
            try:
                file_uploads += get_sensor_files(site)
            except Exception as e:
                logging.error(e)

        # if 'LP' is a keyword, add leaf pack data to file_uploads
        if 'LP' in hydroshare_resource.data_types:
            try:
                file_uploads += get_leafpack_files(site)
            except Exception as e:
                logging.error(e)

        if len(file_uploads):
            upload_hydroshare_resource_files(resource, file_uploads)

    def update_keywords(self, resource, hydroshare_resource=None, site=None):  # type: (Resource, HydroShareResource, SiteRegistration) -> None
        # Clear the resources keywords
        resource.keywords = set()

        if site is None:
            site = SiteRegistration.objects.get(sampling_feature_code=self.kwargs[self.slug_field])

        if hydroshare_resource is None:
            hydroshare_resource = HydroShareResource.objects.filter(site_registration=site.registration_id, visible=True).first()  # type: HydroShareResource

        # Add 'WikiWatershed' keyword to all resources
        resource.keywords.add('WikiWatershed')

        # Check if 'TS' (Time Series) is a selected data type, and add variable names as keywords if True
        if 'TS' in hydroshare_resource.data_types:
            # Add 'EnviroDIY' keyword to resource if sharing time series data
            resource.keywords.add('EnviroDIY')

            sensors = SiteSensor.objects.filter(registration=site)
            if len(sensors):
                # Add sensor variable names as keywords
                for sensor in sensors:
                    output = sensor.sensor_output
                    if output is not None and output.variable_name is not None:
                        resource.keywords.add(output.variable_name)

        # Add the 'Leaf Pack' keyword if sharing leaf pack experiment data
        if 'LP' in hydroshare_resource.data_types and len(site.leafpack_set.all()) > 0:
            resource.keywords.add('Leaf Pack')

        if hydroshare_resource.pk is not None:
            # if 'hydroshare_resource' has a primary key, then 'resource' has already been created
            # and it's 'update_keywords()' method can be invoked.
            resource.update_keywords()

    def get(self, request, *args, **kwargs):
        # # uncomment to force a hydroshare resource file update.
        # # Only do this for debugging purposes!
        # call_command('update_hydroshare_resource_files', '--force-update')
        return super(HydroShareResourceBaseView, self).get(request, args, kwargs)


class HydroShareResourceCreateView(HydroShareResourceBaseView, HydroShareResourceViewMixin):
    template_name = 'hydroshare/hs_site_details.html'
    model = HydroShareResource
    object = None
    fields = '__all__'

    ABSTRACT_PROTO = u"The data contained in this resource were uploaded from the WikiWatershed Data Sharing Portal " \
        u"– http://data.wikiwatershed.org. They were collected at a site named {site_name}. The full URL to access " \
        u"this site in the WikiWatershed Data Sharing portal is: http://data.wikiwatershed.org/sites/{site_code}/."

    TITLE_PROTO = "Data from {site_name} uploaded from the WikiWatershed Data Sharing Portal"

    def generate_abstract(self, site):
        return self.ABSTRACT_PROTO.format(site_name=site.sampling_feature_name, site_code=site.sampling_feature_code)

    def generate_title(self, site):
        return self.TITLE_PROTO.format(site_name=site.sampling_feature_name)

    def get_context_data(self, **kwargs):
        context = super(HydroShareResourceCreateView, self).get_context_data(**kwargs)
        site = SiteRegistration.objects.get(sampling_feature_code=self.kwargs[self.slug_field])
        initial_datatype = HydroShareSettingsForm.data_type_choices[0][0]

        # Cycle through resources to make sure they still exist on hydroshare.org
        resources = HydroShareResource.objects.filter(site_registration=site.pk, visible=False)

        for resource in resources:

            hs_resource = self.get_hs_resource(resource)
            try:
                # Basically, just make request to see if the resource still exists. This request can be anything.
                hs_resource.get_access_level()
            except HydroShareNotFound:
                resource.delete()
            except TokenExpiredError:
                pass

        context['site'] = site
        form = HydroShareSettingsForm(initial={'site_registration': site.pk,
                                               'data_types': [initial_datatype],
                                               'pause_sharing': False,
                                               'title': self.generate_title(site),
                                               'abstract': self.generate_abstract(site)})
        form.fields['resources'].queryset = HydroShareResource.objects.filter(site_registration=site.pk, visible=False)
        context['form'] = form
        return context

    def create_resource(self, site, form):
        hs_account = self.request.user.hydroshare_account

        hydroshare_resource = HydroShareResource(site_registration=site,
                                                 hs_account=hs_account,
                                                 data_types=",".join(form.cleaned_data['data_types']),
                                                 update_freq=form.cleaned_data['update_freq'],
                                                 sync_type=form.cleaned_data['schedule_type'],
                                                 is_enabled=True,
                                                 title=form.cleaned_data['title'],
                                                 last_sync_date=timezone.now())

        token_json = hs_account.get_token()
        client = AuthUtil.authorize(token=token_json).get_client()
        resource = Resource(client)

        resource.owner = Resource.DEFAULT_OWNER
        resource.resource_type = Resource.COMPOSITE_RESOURCE
        resource.creator = '{0} {1}'.format(self.request.user.first_name, self.request.user.last_name)
        resource.abstract = form.cleaned_data['abstract']
        resource.title = form.cleaned_data['title']
        resource.public = True

        coverage = PointCoverage(name=site.sampling_feature_name, latitude=site.latitude, longitude=site.longitude)
        resource.add_coverage(coverage)

        # Add keywords to the resource
        self.update_keywords(resource, hydroshare_resource=hydroshare_resource, site=site)

        try:
            """
            NOTE: The UUID returned when creating a resource on hydroshare.org is externally generated and should only 
            be used as a reference to an external datasource that is not part of the ODM2DataSharingPortal ecosystem.
            """
            hydroshare_resource.ext_id = resource.create()
            hydroshare_resource.title = resource.title
        except HydroShareHTTPException as e:
            return JsonResponse({"error": e.message,
                                 "message": "There was a problem with hydroshare.org and your resource was not created. You might want to see if www.hydroshare.org is working and try again later."},
                                status=e.status_code)

        hydroshare_resource.save()

        return resource

    def post(self, request, *args, **kwargs):
        """
        Creates a resource in hydroshare.org using form data.
        """
        form = HydroShareSettingsForm(request.POST)

        if form.is_valid():
            site = SiteRegistration.objects.get(sampling_feature_code=self.kwargs[self.slug_field])

            if form.cleaned_data['resources']:
                resource = form.cleaned_data['resources']
                resource.visible = True
                resource.data_types = ",".join(form.cleaned_data['data_types'])
                resource.update_freq = form.cleaned_data['update_freq']
                resource.sync_type = form.cleaned_data['schedule_type']
                resource.is_enabled = True
                resource.last_sync_date = timezone.now()
                resource.title = form.cleaned_data['title']
                resource.save()
                hs_resource = self.get_hs_resource(resource)
                hs_resource.update({'title': form.cleaned_data['title'],
                                    'description': form.cleaned_data['abstract']})
            else:
                hs_resource = self.create_resource(site, form)

            try:
                self.upload_hydroshare_files(hs_resource)
            except Exception as e:
                logging.error(e)

            success_url = reverse('site_detail', kwargs={'sampling_feature_code': site.sampling_feature_code})

            if self.request.is_ajax():
                return JsonResponse({'redirect': success_url})
            else:
                return redirect(success_url)
        else:
            return self.form_invalid(form)


class HydroShareResourceUpdateView(HydroShareResourceViewMixin, HydroShareResourceBaseView):
    template_name = 'hydroshare/hs_site_details.html'
    model = HydroShareResource
    slug_field = 'sampling_feature_code'
    slug_url_kwarg = 'hydroshare_settings_id'
    fields = '__all__'
    object = None

    def get_context_data(self, **kwargs):
        context = super(HydroShareResourceUpdateView, self).get_context_data(**kwargs)
        site = SiteRegistration.objects.get(sampling_feature_code=self.kwargs['sampling_feature_code'])
        resource = self.get_object()
        context['site'] = site
        context['resource'] = resource
        context['form'] = HydroShareSettingsForm(initial={
            'site_registration': site.pk,
            'update_freq': resource.update_freq,
            'schedule_type': resource.sync_type,
            'pause_sharing': not resource.is_enabled,
            'data_types': resource.data_types.split(",")
        })

        context['delete_form'] = HydroShareResourceDeleteForm()

        hs_resource = self.get_hs_resource(resource)
        try:
            metadata = hs_resource.get_system_metadata(timeout=10.0)
            context['resource_is_published'] = metadata.get("published", False)

            # Update the title in case the owner changed it
            if 'resource_title' in metadata:
                resource.title = metadata['resource_title']
                resource.save()

        except HydroShareNotFound:
            context['resource_not_found'] = True
        except requests.exceptions.Timeout:
            context['request_timeout'] = True
        finally:
            # if the resource was not found or the resource is published, provide the 'delete_resource_url'
            if context.get('resource_not_found', None) is True or context.get('resource_is_published', None):
                context['delete_resource_url'] = reverse('hydroshare:delete',
                                                         kwargs={'sampling_feature_code': site.sampling_feature_code})

        return context

    def post(self, request, *args, **kwargs):
        form = HydroShareSettingsForm(request.POST)

        if form.is_valid():
            site = SiteRegistration.objects.get(pk=form.cleaned_data['site_registration'])
            hydroshare_resource = self.get_object()  # type: HydroShareResource

            if 'update_files' in request.POST and hydroshare_resource.is_enabled:
                # get hydroshare resource info using hydroshare_util; this will get authentication info needed to
                # upload files to the resource.
                resource = self.get_hs_resource(hydroshare_resource)  # type: Resource

                # Upload the most recent resource files
                try:
                    # update hs_resource's keywords
                    self.update_keywords(resource, hydroshare_resource=hydroshare_resource, site=site)

                    # update the files
                    self.upload_hydroshare_files(resource)
                except Exception as e:
                    return JsonResponse({'error': e.message}, status=500)

                # update last sync date on resource
                hydroshare_resource.last_sync_date = timezone.now()
            else:
                hydroshare_resource.data_types = ",".join(form.cleaned_data['data_types'])
                hydroshare_resource.update_freq = form.cleaned_data['update_freq']
                hydroshare_resource.sync_type = form.cleaned_data['schedule_type']
                hydroshare_resource.is_enabled = not form.cleaned_data["pause_sharing"]

                hydroshare_resource.save()



            success_url = reverse('site_detail', kwargs={'sampling_feature_code': site.sampling_feature_code})
            if self.request.is_ajax():
                return JsonResponse({'redirect': success_url})
            else:
                return redirect(success_url)
        else:
            response = self.form_invalid(form)
            return response


class HydroShareResourceDeleteView(LoginRequiredMixin, HydroShareResourceViewMixin, DeleteView):
    model = HydroShareResource
    slug_field = 'sampling_feature_code'
    slug_url_kwarg = 'sampling_feature_code'

    def get_site_registration(self):
        try:
            code = self.kwargs.get('sampling_feature_code', '')
            site = SiteRegistration.objects.get(sampling_feature_code=code)
        except ObjectDoesNotExist:
            return None
        return site

    def get_object(self, queryset=None, **kwargs):
        site = kwargs['site']
        resource = None
        try:
            # Find the resource that is currently visible; there should only be one.
            resource = HydroShareResource.objects.filter(site_registration=site.registration_id, visible=True).first()
        except ObjectDoesNotExist:
            pass
        return resource

    def get(self, request, *arg, **kwargs):
        site = self.get_site_registration()
        return redirect(reverse('site_detail', kwargs={'sampling_feature_code': site.sampling_feature_code}))

    def post(self, request, *args, **kwargs):
        site = self.get_site_registration()
        resource = self.get_object(site=site)

        form = HydroShareResourceDeleteForm(request.POST)
        if form.is_valid():
            delete_external_resource = form.cleaned_data.get('delete_external_resource')

            if delete_external_resource is True:
                # delete resource in hydroshare.org if delete_external_resource is True
                hs_resource = self.get_hs_resource(resource)
                try:
                    hs_resource.delete()
                except Exception as error:
                    print(error)
                resource.delete()
            else:
                # Don't delete the resource, but instead turn visibility off. This is so the user can reconnect the
                # resource after disconnecting it.
                resource.visible = False
                resource.save()

        return redirect(reverse('site_detail', kwargs={'sampling_feature_code': site.sampling_feature_code}))


class OAuthAuthorize(TemplateView):
    """handles the OAuth 2.0 authorization workflow with hydroshare.org"""
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated():
            return HttpResponseServerError('You are not logged in!')

        if 'code' in request.GET:
            try:
                token_dict = AuthUtil.authorize_client_callback(request)  # type: dict
                auth_util = AuthUtil.authorize(token=token_dict)  # type: AuthUtil
            except Exception as e:
                print('Authorizition failure: {}'.format(e))
                return HttpResponse(mark_safe("<p>Error: Authorization failure!</p><p>{e}</p>".format(e=e)))

            client = auth_util.get_client()  # type: HydroShareAdapter
            user_info = client.getUserInfo()
            print('\nuser_info: %s', json.dumps(user_info, indent=3))

            try:
                # check if hydroshare account already exists
                account = HydroShareAccount.objects.get(ext_id=user_info['id'])
            except ObjectDoesNotExist:
                # if account does not exist, create a new one
                account = HydroShareAccount(is_enabled=True, ext_id=user_info['id'])

            if account.token:
                account.token.delete()
                account.save()

            # Make updates to datatbase
            account.token = OAuthToken.objects.create(**token_dict)
            account.user = request.user
            account.save()

            return redirect('user_account')
        elif 'error' in request.GET:
            return HttpResponseServerError(request.GET['error'])
        else:
            return AuthUtil.authorize_client(request)


class OAuthRedirect(TemplateView):
    """
    handles notifying a user they are being redirected, then handles the actual redirection

    When a user comes to this view, 'self.get()' checks for a 'redirect' value in the url parameters.

        - If the value is found, the user will be immediately redirected to www.hydroshare.org for client
        authorization.

        - If the value is NOT found, the user is sent to a page notifying them that they are about to be redirected.
        After a couple of seconds, they are redirected back to this view with the 'redirect' parameter contained in the
        url, and sent off to www.hydroshare.org.
    """
    template_name = 'hydroshare/oauth_redirect.html'

    def get_context_data(self, **kwargs):
        context = super(OAuthRedirect, self).get_context_data(**kwargs)

        # Get the current scheme (http or https)
        scheme = self.request.is_secure() and "https" or "http"
        # Need to get the host since the host name can be 'data.envirodiy.org' or 'data.wikiwatershed.org'
        host = self.request.META.get('HTTP_HOST', None)
        # Build the url and add 'redirect' into the url params
        url = '{scheme}://{host}{url}?{params}'.format(scheme=scheme, host=host,
                                                       url=reverse('hydroshare:oauth_redirect'), params='redirect=true')

        context['redirect_url'] = mark_safe(url)

        return context

    def get(self, request, *args, **kwargs):
        if 'redirect' in request.GET and request.GET['redirect'] == 'true':
            return AuthUtil.authorize_client(request)

        return super(OAuthRedirect, self).get(request, args, kwargs)


# def get_site_files(site_registration):
#     site_sensors = SiteSensor.objects.filter(registration=site_registration.pk)
#     files = []
#     for site_sensor in site_sensors:
#         filename, csv_file = CSVDataApi.get_csv_file(site_sensor.result_id)
#         files.append((filename, csv_file.getvalue()))
#
#     leafpacks = LeafPack.objects.filter(site_registration=site_registration.pk)
#     for leafpack in leafpacks:
#         filename, csv_file = get_leafpack_csv(site_registration.sampling_feature_code, leafpack.id)
#         files.append((filename, csv_file))
#
#     return files


def get_sensor_files(site_registration):
    queryset = SiteSensor.objects.filter(registration=site_registration.pk)
    files = []
    for site_sensor in queryset:
        filename, csv_file = CSVDataApi.get_csv_file(site_sensor.result_id)
        files.append((filename, csv_file.getvalue()))
    return files


def get_leafpack_files(site_registration):
    leafpacks = LeafPack.objects.filter(site_registration=site_registration.pk)
    files = []
    for leafpack in leafpacks:
        filename, csv_file = get_leafpack_csv(site_registration.sampling_feature_code, leafpack.id)
        files.append((filename, csv_file))
    return files


def upload_hydroshare_resource_files(resource, files):  # type: (Resource, [object]) -> None

    if isinstance(resource, JsonResponse):
        # This might happen if hydroshare isn't working...
        raise Exception(resource.content)

    for file_ in files:
        file_name = file_[0]
        content = file_[1]

        if '.csv' not in file_name:
            file_name += '.csv'

        resource.upload_file(file_name, content)
