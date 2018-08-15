from leafpack.models import Macroinvertebrate
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
import requests
import csv
import cStringIO
from django.conf import settings
import logging


class Command(BaseCommand):

    def handle(self, *args, **options):

        try:
            api_key = settings.GOOGLE_API_CONF['api_key']
            file_id = settings.GOOGLE_API_CONF['files']['taxon_spreadsheet']
        except KeyError:
            print("Update failed, you need to add 'google_api_conf' in settings.json. See the 'settings_template.json' example for help.")
            return

        url_base = 'https://www.googleapis.com/drive/v3/files/{file_id}/export?mimeType=text%2Fcsv&key={key}'

        request = requests.get(url_base.format(file_id=file_id, key=api_key))

        if request.status_code != 200:
            return

        data = request.content

        reader = csv.DictReader(cStringIO.StringIO(data), delimiter=',')

        current_taxons = Macroinvertebrate.objects.all()

        for row in reader:
            taxon_name = row.get('TaxonName', '')

            if taxon_name == '':
                continue

            if '#' == taxon_name[0]:
                continue

            common_name = row['CommonName']
            parent_name = row.get('Parent Taxon', None)
            itis_serial_num = row.get('ITIS Taxonomic Serial Number', None)
            pollution_tolerance = row.get('Pollution Tolerance', 0)
            sort_priority = row.get('Sort Priority', 9999)
            url = row['URL']

            taxon = None

            for t in current_taxons:
                if taxon_name.lower() in t.scientific_name.lower() or t.scientific_name.lower() in taxon_name.lower():
                    taxon = t
                    break

            if taxon is None:
                taxon = Macroinvertebrate()

            taxon.scientific_name = taxon.latin_name = taxon_name
            taxon.common_name = common_name
            taxon.itis_serial_number = itis_serial_num
            taxon.url = url
            taxon.pollution_tolerance = pollution_tolerance
            taxon.sort_priority = sort_priority

            if len(parent_name):

                try:
                    parent = Macroinvertebrate.objects.get(scientific_name__iregex=parent_name)
                    taxon.family_of = parent
                except ObjectDoesNotExist:
                    continue

            try:
                taxon.save()
            except IntegrityError as e:
                logging.error(e)






