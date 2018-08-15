# adapter.py
import requests
from hs_restclient import HydroShare, DEFAULT_HOSTNAME, HydroShareNotAuthorized, HydroShareNotFound, \
    HydroShareHTTPException, default_progress_callback
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
from oauthlib.oauth2.rfc6749.errors import TokenExpiredError


class HydroShareAdapter(HydroShare):
    def __init__(self, hostname=DEFAULT_HOSTNAME, port=None, use_https=True, verify=True,
                 auth=None, default_headers=None):
        self._default_headers = default_headers
        super(HydroShareAdapter, self).__init__(hostname=hostname, port=port, use_https=use_https, verify=verify,
                                                auth=auth)

    def _build_params(self, params):  # type: (dict) -> str
        param_vals = ['{param}={val}'.format(param=p, val=v) for p, v in params.iteritems()]
        return "?{params}".format(params="&".join(param_vals))

    def _request(self, method, url, params=None, data=None, files=None, headers=None, stream=False, **kwargs):

        timeout = None
        if 'timeout' in kwargs:
            timeout = kwargs.get('timeout', None)

        if self._default_headers and headers:
            headers.update(self._default_headers)
        elif self._default_headers:
            headers = self._default_headers

        return self.session.request(method, url, params=params, data=data, files=files, headers=headers,
                                       stream=stream, verify=self.verify, timeout=timeout, **kwargs)

    def getSystemMetadata(self, pid, **kwargs):
        """
        Returns system metadata for a resource which includes the dublin core elements
        Note: HydroShareAdapter overrides it's super class method, getSystemMetadata(), so 'timeout' can be
        included in **kwargs. By default, the requests library does not have timeout limit for HTTP requests, and
        some views wait for getSystemMetadata() to complete an HTTP request to hydroshare.org before the views are
        rendered.
        """
        timeout = None
        if 'timeout' in kwargs:
            timeout = kwargs.get('timeout', None)

        url = "{url_base}/resource/{pid}/sysmeta/".format(url_base=self.url_base,
                                                          pid=pid)
        headers = self._default_headers

        access_token = self.auth.token.get('access_token', None)
        if access_token is not None:
            headers['Authorization'] = 'Bearer {0}'.format(access_token)

        req = requests.get(url, headers=headers, timeout=timeout)
        if req.status_code != 200:
            if req.status_code == 403:
                raise HydroShareNotAuthorized((req.request.method, url))
            elif req.status_code == 404:
                raise HydroShareNotFound((pid,))
            else:
                raise HydroShareHTTPException((url, req.request.method, req.status_code))

        return req.json()

    def addResourceFile(self, pid, resource_file, resource_filename=None, progress_callback=None):
        url = "{url_base}/resource/{pid}/files/".format(url_base=self.url_base,
                                                        pid=pid)

        params = {}
        close_fd = self._prepareFileForUpload(params, resource_file, resource_filename)

        encoder = MultipartEncoder(params)
        if progress_callback is None:
            progress_callback = default_progress_callback
        monitor = MultipartEncoderMonitor(encoder, progress_callback)

        r = self._request('POST', url, data=monitor, headers={'Content-Type': monitor.content_type,
                                                              'Connection': 'keep-alive',
                                                              'Keep-Alive': 'timeout=10, max=1000'})

        if close_fd:
            fd = params['file'][1]
            fd.close()

        if r.status_code != 201:
            if r.status_code == 403:
                raise HydroShareNotAuthorized(('POST', url))
            elif r.status_code == 404:
                raise HydroShareNotFound((pid,))
            else:
                raise HydroShareHTTPException((url, 'POST', r.status_code))

        response = r.json()
        assert (response['resource_id'] == pid)

        return response['resource_id']

    def getAccessRules(self, pid):
        """
        Get access rule for a resource.
        """
        url = "{url_base}/resource/{pid}/access/".format(url_base=self.url_base, pid=pid)

        r = self._request('GET', url)
        if r.status_code != 200:
            if r.status_code == 403:
                raise HydroShareNotAuthorized(('GET', url))
            elif r.status_code == 404:
                raise HydroShareNotFound((pid,))
            else:
                raise HydroShareHTTPException((url, 'GET', r.status_code))

        return r.json()

    def updateKeywords(self, pid, keywords):  # type: (str, set) -> object
        url = "{url_base}/resource/{pid}/scimeta/elements/".format(url_base=self.url_base, pid=pid)

        subjects = []
        for keyword in keywords:
            subjects.append({"value": keyword})

        r = self.session.request('PUT', url, json={"subjects": subjects})
        if r.status_code != 202:
            if r.status_code == 403:
                raise HydroShareNotAuthorized(('PUT', url))
            elif r.status_code == 404:
                raise HydroShareNotFound((pid,))
            else:
                raise HydroShareHTTPException((url, 'PUT', r.status_code, keywords))
        else:
            return r.json().get('subjects', dict())
