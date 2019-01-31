import json
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection, connections, transaction

from dataloader.models import Organization, Variable, Unit, Result
from dataloaderinterface.models import SiteSensor
from tsa.helpers import TimeSeriesAnalystHelper


class Command(BaseCommand):
    help = 'Delete and rebuild the TSA Catalog table.'

    def handle(self, *args, **options):
        sensors = SiteSensor.objects.select_related('registration').prefetch_related('last_measurement', 'sensor_output')\
            .filter(last_measurement__isnull=False, sensor_output__isnull=False)\
            .defer('height', 'sensor_notes', 'registration__site_notes')

        with connections['tsa_catalog'].cursor() as cursor:
            print("- DELETING EVERYTHING!")
            cursor.execute('TRUNCATE TABLE public."DataSeries" RESTART IDENTITY')
            cursor.execute('ALTER SEQUENCE public.series_increment RESTART WITH 1;')

        helper = TimeSeriesAnalystHelper()
        print("-Generating all data series...")
        helper.create_series_from_sensors(sensors)
        print("-DONE!")
