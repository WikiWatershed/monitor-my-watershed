import csv
import io
import re
from streamwatch import models
from dataloaderinterface.models import SiteRegistration


class StreamWatchCSVWriter(object):
    CSV_DIALECT = csv.excel
    DEFAULT_DASH_LENGTH = 20
    HYPERLINK_BASE_URL = 'http://data.wikiwatershed.org'

    def __init__(self, streamwatch, site):  # type: (streamwatch, SiteRegistration) -> None
        self.streamwatch = streamwatch
        self.site = site

        self.output = io.BytesIO()
        self.writer = csv.writer(self.output, dialect=self.CSV_DIALECT)

    def filename(self):
        # filename format: {Sampling Feature Code}_{Placement date}_{zero padded streamwatch id}.csv
        return '{}_{}_{:03d}.csv'.format(self.site.sampling_feature_code,
                                         self.streamwatch.collect_date, int(self.streamwatch.action_id))

    def write(self):
        streamwatch = self.streamwatch
        site_registration = self.site

        # Write file header
        self.writerow(['StreamWatch Survey Details'])
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

        # write streamwatch data
        # todo: separate into different activities:
        self.make_header(['StreamWatch Survey Details'])
        for key, value in data.items():
            self.writer.writerow([key.title(), value])
        self.writerow(['URL', '{0}/sites/{1}/{2}'.format(self.HYPERLINK_BASE_URL,
                                                         site_registration.sampling_feature_code,
                                                         streamwatch.action_id)])

    def read(self):
        return self.output.getvalue()

    def writerow(self, *args):
        self.writer.writerow(*args)

    def make_header(self, rows):
        self.writerow(rows)
        self.dash_line(len(rows[0]))

    def dash_line(self, dash_count=None):
        if dash_count is None:
            dash_count = self.DEFAULT_DASH_LENGTH
        self.writerow(['-' * dash_count])

    def blank_line(self):
        self.writerow([])








