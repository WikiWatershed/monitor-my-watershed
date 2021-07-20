import logging
import os
import json
from django.http import Http404
from tempfile import mkstemp
from re import search as regex_search
from hs_restclient import HydroShareNotFound, HydroShareNotAuthorized
from hydroshare_util.adapter import HydroShareAdapter
from . import HydroShareUtilityBaseClass
from hydroshare_util.coverage import CoverageFactory, Coverage

TMP_FILE_PATH = '~$hydroshare_tmp_files'


class Resource(HydroShareUtilityBaseClass):
    RESOURCE_TYPES = None
    COMPOSITE_RESOURCE = 'CompositeResource'
    DEFAULT_OWNER = 'HydroShare'

    def __init__(self, client, raw=None, resource_id=None, creator=None, title="", abstract="", keywords=set(),
                 funding_agency=None, agency_url=None, award_title="", award_number=None, files=list(), subjects=list(),
                 period_start=None, period_end=None, public=False, resource_map_url=None, resource_url=None,
                 date_created=None, date_last_updated=None, discoverable=None, published=None, resource_type=None,
                 immutable=None, science_metadata_url=None, bag_url=None, coverages=list(), shareable=None, **kwargs):

        self.client = client  # type: HydroShareAdapter
        self._raw = raw

        self.abstract = abstract
        self.award_number = award_number
        self.award_title = award_title
        self.agency_url = agency_url
        self.bag_url = bag_url
        self.creator = self.owner = creator
        self.date_created = date_created
        self.date_last_updated = date_last_updated
        self.discoverable = discoverable
        self.files = files
        self.funding_agency = funding_agency
        self.immutable = immutable
        self.keywords = keywords
        self.period_end = period_end
        self.period_start = period_start
        self.public = True if isinstance(public, str) and public.lower() == 'true' else bool(public)
        self.published = published
        self.resource_id = resource_id
        self.resource_map_url = resource_map_url
        self.resource_title = self.title = title
        self.resource_type = resource_type
        self.resource_url = resource_url
        self.science_metadata_url = science_metadata_url
        self.shareable = shareable
        self.subjects = subjects
        self.rights = 'http://creativecommons.org/licenses/by-sa/4.0/'  # Creative Commons Attribution-ShareAlike CC BY-SA

        if isinstance(public, str):
            self.public = True if public.lower() == 'true' else False
        else:
            self.public = bool(public)

        self.coverages = list()
        for coverage in coverages:
            if isinstance(coverage, dict):
                self.coverages.append(CoverageFactory(coverage=coverage))
            elif isinstance(coverage, Coverage):
                self.coverages.append(coverage)

        for key, value in kwargs.iteritems():
            if key == 'public':
                if isinstance(value, str):
                    self.public = True if value.lower() == 'true' else False
                else:
                    self.public = bool(value)
            else:
                setattr(self, key, value)

    def add_coverage(self, coverage):
        if isinstance(coverage, Coverage):
            self.coverages.append(coverage)
        else:
            self.coverages.append(CoverageFactory(coverage=coverage))

    def update_file_list(self):
        try:
            file_list = [file_ for file_ in self.client.getResourceFileList(self.resource_id)]
            self.files = [os.path.basename(file_['url']) for file_ in file_list]
        except Exception as e:
            self._log("Error updating resource file list", error=e)

    def get_system_metadata(self, **kwargs):
        return self.client.getSystemMetadata(self.resource_id, **kwargs)

    def get_science_metadata(self):
        return self.client.getScienceMetadata(self.resource_id)

    def update_metadata(self, data=None):
        if data is None:
            data = self.to_object()
        return self.client.updateScienceMetadata(self.resource_id, data)

    def upload_files(self):
        upload_success_count = 0
        for file_ in self.files:
            try:
                self.client.deleteResourceFile(self.resource_id, os.path.basename(file_))
            except HydroShareNotFound:
                pass

            if not isinstance(file_, str):
                file_ = str(file_)

            try:
                self.client.addResourceFile(self.resource_id, file_)
                self._log("File upload successful: '{filename}'".format(filename=os.path.basename(file_)),
                          level=logging.INFO)
                upload_success_count += 1
            except KeyError as e:
                self._log_error('File upload failed; incorrectly formatted arguments given.', e)
                raise e
            except Exception as e:
                self._log_error("File upload failed: \n\t{fname}\n".format(fname=os.path.basename(file_)), e)
                raise e
        self._log("successfully uploaded {count} files".format(count=upload_success_count),
                  level=logging.INFO)

    def upload_file(self, filename, content):
        if self.resource_id is None:
            raise HydroShareNotFound((self.resource_id, "resource has no resource_id"))

        try:
            self.client.deleteResourceFile(self.resource_id, filename)
        except HydroShareNotFound:
            # If file doesn't exist on hydroshare, it's okay, just keep breathing.
            pass
        except HydroShareNotAuthorized:
            pass

        # Write file to disk... because that's how hs_restclient needs it to be done!
        suffix = '.csv' if regex_search('\.csv', filename) else ''
        fd, path = mkstemp(suffix=suffix)

        with open(path, 'w+') as f:
            f.write(content)

        # upload file
        try:
            return self.client.addResourceFile(self.resource_id, path, resource_filename=filename)
        except HydroShareNotFound:
            raise Http404(u"Resource '{0}' was not found".format(self.resource_id))
        except Exception as e:
            raise e
        finally:
            # close the file descriptor
            os.close(fd)

            # delete the tmp file
            os.remove(path)

    def delete_files(self, files=None):
        if files is None:
            self.update_file_list()
            files = self.files

        for file_ in files:
            url = file_['url']
            self._log("Deleting resource file\n\tfile: {file}".format(file=os.path.basename(url)),
                      level=logging.INFO)
            self.client.deleteResourceFile(self.resource_id, os.path.basename(url))

    def get_coverage_period(self):
        raise NotImplementedError("method not implemented.")

    def delete(self):
        self._log("Deleting resource!", level=logging.INFO)
        self.client.deleteResource(self.resource_id)

    def create(self):
        metadata = []
        for coverage in self.coverages:
            coverage_dict = {"coverage": coverage.to_dict()}
            metadata.append(coverage_dict)

        self.resource_id = self.client.createResource(resource_type=self.resource_type,
                                                      title=self.title,
                                                      metadata=json.dumps(metadata, encoding='ascii'),
                                                      keywords=list(self.keywords),
                                                      abstract=self.abstract)

        # Set access level after the resource is created since you can't seem to set the access rule at creation.
        if self.public is not None:
            try:
                self.client.setAccessRules(self.resource_id, self.public)
            except Exception as e:
                print('Error: unknown error occured, resource access level could not be updated: {}'.format(e.message))

        return self.resource_id

    def update(self, data=None):
        if data is None:
            data = self.to_object()

        if 'keywords' in data:
            data['subjects'] = []

            for keyword in data['keywords']:
                data['subjects'].append({"value": keyword})

            del data['keywords']

        return self.client.updateScienceMetadata(self.resource_id, data)

    def update_keywords(self, keywords=None):  # type: (list) -> object
        if keywords is None:
            keywords = self.keywords

        return self.client.updateKeywords(self.resource_id, keywords)

    def to_object(self, clean=True):
        metadata = super(Resource, self).to_object(clean=clean)

        # replace keyword 'coverages' with 'coverage'...
        metadata['coverage'] = getattr(metadata, 'coverages', list())
        if 'coverages' in metadata:
            del metadata['coverages']

        if self.coverages and len(self.coverages) > 0:
            metadata['coverage'] = list()
            for coverage in self.coverages:
                if isinstance(coverage, Coverage):
                    metadata['coverage'].append(coverage.to_dict())

        for key, value in metadata.iteritems():
            if isinstance(value, set):
                metadata[key] = list(value)  # change sets into lists because sets are not json serializeable

        return metadata

    def make_public(self, public=True):
        return self.client.setAccessRules(self.resource_id, public=public)

    def get_access_level(self):
        """
        Returns the access level of the resource (public or private)
        """
        return self.client.getAccessRules(self.resource_id)

    def to_dict(self):
        return {
            'abstract': self.abstract,
            'agency_url': self.agency_url,
            'award_title': self.award_title,
            'award_number': self.award_number,
            'bag_url': self.bag_url,
            'creator': self.creator,
            'date_created': self.date_created,
            'date_last_updated': self.date_last_updated,
            'discoverable': self.discoverable,
            'files': self.files,
            'funding_agency': self.funding_agency,
            'immutable': self.immutable,
            'keywords': self.keywords,
            'period_end': self.period_end,
            'period_start': self.period_start,
            'public': self.public,
            'published': self.published,
            'resource_id': self.resource_id,
            'resource_map_url': self.resource_map_url,
            'resource_title': self.resource_title,
            'resource_type': self.resource_type,
            'resource_url': self.resource_url,
            'science_metadata_url': self.science_metadata_url,
            'shareable': self.shareable,
            'subjects': self.subjects,
            'coverages': [coverage.to_dict() for coverage in self.coverages] if isinstance(self.coverages, list) else []
        }

    def _log_error(self, msg, error):
        return self._log(msg, error=error, level=logging.ERROR)

    def _log(self, msg, error=None, level=None):
        if error:
            log = "{msg}\n\tresource_id: {id}\n\t{e}".format(msg=msg, id=self.resource_id, e=error)
        else:
            log = "{msg}\n\tresource_id: {id}".format(msg=msg, id=self.resource_id)

        if isinstance(level, str):
            level = level.lower()
        elif level is None:
            level = logging.DEBUG

        if level == logging.DEBUG or level == 'debug':
            logging.debug(log)
        elif level == logging.INFO or level == 'info':
            logging.info(log)
        elif level == logging.WARN or level == logging.WARNING or level == 'warning' or level == 'warn':
            logging.warning(log)
        elif level == logging.ERROR or level == 'error':
            logging.error(log)
        elif level == logging.CRITICAL or level == 'critical':
            logging.critical(log)

    def __str__(self):
        return '{title} with {lenfiles} files'.format(title=self.title, lenfiles=len(self.files))

    def __repr__(self):
        return "<{classname}: {title}>".format(classname=self.classname, title=self.title)


__all__ = ["Resource"]
