import csv
import io
import re
from leafpack.models import LeafPack, LeafPackBug, LeafPackType, Macroinvertebrate
from dataloaderinterface.models import SiteRegistration


class LeafPackCSVWriter(object):
    CSV_DIALECT = csv.excel
    DEFAULT_DASH_LENGTH = 20
    HYPERLINK_BASE_URL = 'http://data.wikiwatershed.org'

    def __init__(self, leafpack, site):  # type: (LeafPack, SiteRegistration) -> None
        self.leafpack = leafpack
        self.site = site

        self.output = io.BytesIO()
        self.writer = csv.writer(self.output, dialect=self.CSV_DIALECT)

    def filename(self):
        # filename format: {Sampling Feature Code}_{Placement date}_{zero padded leafpack id}.csv
        return '{}_{}_{:03d}.csv'.format(self.site.sampling_feature_code,
                                         self.leafpack.placement_date, int(self.leafpack.id))

    def write(self):
        leafpack = self.leafpack
        site_registration = self.site

        data = self.get_data()

        # Write file header
        self.writerow(['Leaf Pack Experiment Details'])
        self.make_header(['These data were copied to HydroShare from the WikiWatershed Data Sharing Portal.'])

        self.blank_line()

        # write site registration information
        self.make_header(['Site Information'])

        self.writerow(['Site Code', site_registration.sampling_feature_code])
        self.writerow(['Site Name', site_registration.sampling_feature_name])
        self.writerow(['Site Description', site_registration.sampling_feature.sampling_feature_description])
        self.writerow(['Latitude', site_registration.latitude])
        self.writerow(['Longitude', site_registration.longitude])
        self.writerow(['Elevation (m)', site_registration.elevation_m])
        self.writerow(['Vertical Datum', site_registration.sampling_feature.elevation_datum])
        self.writerow(['Site Type', site_registration.site_type])
        self.writerow(['URL', '{0}/sites/{1}/'.format(self.HYPERLINK_BASE_URL,
                                                      site_registration.sampling_feature_code)])

        self.blank_line()

        # write leafpack data
        self.make_header(['Leaf Pack Details'])
        for key, value in data.items():
            self.writer.writerow([key.title(), value])
        self.writerow(['URL', '{0}/sites/{1}/{2}'.format(self.HYPERLINK_BASE_URL,
                                                         site_registration.sampling_feature_code,
                                                         leafpack.id)])

        self.blank_line()

        # write taxon names and corresponding count
        self.make_header(['Macroinvertebrate Counts'])

        for lpg in LeafPackBug.objects.filter(leaf_pack=leafpack)\
                .order_by('bug__pollution_tolerance')\
                .order_by('-bug__sort_priority'):

            if lpg.bug.family_of is not None:
                # prepend a '-' to suborder taxons
                taxon_name = ' - {0} ({1})'.format(lpg.bug.common_name.title(), lpg.bug.scientific_name.title())
            else:
                taxon_name = '{0} ({1})'.format(lpg.bug.common_name.title(), lpg.bug.scientific_name.title())

            self.writer.writerow([taxon_name, lpg.bug_count])

        self.blank_line()

        # write water quality index values
        self.make_header(['Water Quality Index Values'])
        self.writerow(['Total number of individuals found', str(leafpack.taxon_count())])
        PTI_score = leafpack.PTI_score()
        self.writerow(['Pollution Tolerance Index', round(PTI_score, 2)])
        self.writerow(['Pollution Tolerance Index Rating', leafpack.PollutionToleranceIndexRating(PTI_score=PTI_score)])
        self.writerow(['Percent EPT', round(leafpack.percent_EPT(), 2)])


    def read(self):
        return self.output.getvalue()

    def writerow(self, *args):
        self.writer.writerow(*args)

    def get_data(self):
        data = dict()
        ignored_fields = ('id', 'uuid')
        lp_fields = LeafPack._meta.get_fields()

        for field in lp_fields:
            field_value = None

            if field.is_relation and field.name == 'types':
                types = getattr(self.leafpack, field.name, None)

                if types is not None:
                    field_value = ', '.join([t.name for t in types.all()])

            elif field.is_relation:

                continue

            else:

                field_value = getattr(self.leafpack, field.name, None)

            if field_value is not None and field.name not in ignored_fields:
                if field.name == 'types':
                    field_name = 'Leaf Pack Types and Composition'
                else:
                    field_name = " ".join(field.name.split("_"))

                if 'leafpack' in field_name.lower():
                    field_name = re.sub('leafpack', 'Leaf Pack', field_name)

                data[field_name] = str(field_value)

        return data

    def make_header(self, rows):
        self.writerow(rows)
        self.dash_line(len(rows[0]))

    def dash_line(self, dash_count=None):
        if dash_count is None:
            dash_count = self.DEFAULT_DASH_LENGTH
        self.writerow(['-' * dash_count])

    def blank_line(self):
        self.writerow([])








