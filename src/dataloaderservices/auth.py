from rest_framework import authentication
from rest_framework import exceptions

from django.db.models.expressions import Subquery, OuterRef

from dataloader.models import SamplingFeature
from dataloaderinterface.models import SiteRegistration


class UUIDAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        if request.META['REQUEST_METHOD'] != 'POST':
            return None

        if 'HTTP_TOKEN' not in request.META:
            raise exceptions.ParseError("Registration Token not present in the request.")
        elif 'sampling_feature' not in request.data:
            raise exceptions.ParseError("Sampling feature UUID not present in the request.")

        # Get auth_token(uuid) from header,
        # get registration object with auth_token,
        # get the user from that registration,
        # verify sampling_feature uuid is registered by this user,
        # be happy.
        token = request.META['HTTP_TOKEN']
        registration = SiteRegistration.objects.filter(registration_token=token
            ).annotate(sampling_feature_uuid=Subquery(
                SamplingFeature.objects.filter(
                    pk=OuterRef("sampling_feature_id")
                ).values("sampling_feature_uuid")[:1])
            ).values("sampling_feature_uuid").first()
        if not registration:
            raise exceptions.PermissionDenied('Invalid Security Token')

        # request needs to have the sampling feature uuid of the registration -
        if str(registration["sampling_feature_uuid"]) != request.data['sampling_feature']:
            raise exceptions.AuthenticationFailed('Site Identifier is not associated with this Token')

        return None
