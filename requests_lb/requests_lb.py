import dns.resolver
import logging
import random
import requests
import sys
import time


log = logging.getLogger(__name__)


def sample_provider(choices):
    """
    Default sample provider.
    """

    if len(choices) == 0:
        raise Exception('No choices')

    return random.sample(choices, 1)[0]


def srv_provider(**kw):
    """
    Default SRV provider.
    """

    resolver = dns.resolver.Resolver()
    resolver.timeout = 5
    resolver.lifetime = 5

    def fn(name):
        answers = resolver.query(name, 'SRV')
        return set((str(a.target), a.port) for a in answers)

    return fn


class RequestsLB:
    def __init__(self, target, **kw):
        self._s = requests.Session()

        self._target = target
        self._protocol = kw.get('protocol', 'http')

        self._time = kw.get('time_provider', time.time)
        self._srv = kw.get('srv_provider', srv_provider)(**kw)
        self._sample = kw.get('sample_provider', sample_provider)
        self._srv_update_timeout = kw.get('srv_timeout', 30)
        self._bad_host_timeout = kw.get('bad_host_timeout', 2)
        self._max_request_retries = kw.get('max_request_retries', 3)

        self._srv_host = None
        self._srv_bad_hosts = dict()
        self._srv_hosts = set()
        self._srv_last_update = None

    def _srv_filter(self, records):
        """
        Filter out bad records from a set of results.
        """

        return set(records) - set(self._srv_bad_hosts.keys())

    def _srv_mark_bad_host(self, host_entry):
        """
        Mark that a host entry is considered 'bad'.

        Future SRV lookups containing this record will ignore it until the bad
        has expired.
        """

        log.debug("SRV marking bad host %s", host_entry)
        self._srv_bad_hosts[host_entry] = self._time()
        self._srv_hosts.discard(host_entry)

    def _srv_reintroduce_bad_hosts(self):
        """
        Reintroduce a previously marked bad host into the SRV cache.
        """

        for (host_entry, bad_since) in list(self._srv_bad_hosts.items()):
            diff = self._time() - bad_since

            if diff < self._bad_host_timeout:
                continue

            log.debug("SRV reintroducing host %s", host_entry)
            self._srv_bad_hosts.pop(host_entry)
            self._srv_hosts.add(host_entry)

    def _srv_is_expired(self):
        """
        Check if local SRV cache is expired.
        """

        if self._srv_last_update is None:
            return True

        diff = self._time() - self._srv_last_update
        return diff >= self._srv_update_timeout

    def _srv_next_host(self):
        """
        Get the next host to send request to.
        """

        if self._srv_is_expired():
            log.debug('SRV cache expired')
            hosts = self._srv_filter(self._srv(self._target))
            log.debug('SRV new hosts: %s', hosts)

            if len(hosts) == 0:
                raise Exception("No hosts resolved")

            self._srv_hosts = hosts

        self._srv_reintroduce_bad_hosts()

        if len(self._srv_hosts) == 0:
            raise Exception("No hosts available")

        # Current selected host is not an SRV member any more.
        if self._srv_host not in self._srv_hosts:
            self._srv_host = None

        # Selected host is good, re-use.
        if self._srv_host is not None:
            return self._srv_host

        self._srv_host = self._sample(self._srv_hosts)
        return self._srv_host

    def _retry_request(self, fn, target, **kw):
        """
        Send the given request, as defined by the `fn` argument to the given
        target.
        """
        max_request_retries = self._max_request_retries

        if target[0] == '/':
            target = target[1:]

        while max_request_retries > 0:
            host_entry = self._srv_next_host()
            (host, port) = host_entry
            url = "{}://{}:{}/{}".format(self._protocol, host, port, target)

            try:
                response = fn(url, **kw)
            except:
                log.error("request failed: %s", host_entry,
                          exc_info=sys.exc_info())
                self._srv_mark_bad_host(host_entry)
                max_request_retries -= 1
                continue

            if response.status_code == 503:
                log.error("host responded with 503: %s", host_entry)
                self._srv_mark_bad_host(host_entry)
                max_request_retries -= 1
                continue

            return response

        raise Exception("Maximum number of retries attempted")

    def _request_fn(self, method):
        s = self._s

        def _fn(url, **kw):
            return s.request(method, url, **kw)

        return _fn

    def request(self, method, target, **kw):
        fn = self._request_fn(method)
        return self._retry_request(fn, target, **kw)

    def get(self, target, **kw):
        return self._retry_request(self._s.get, target, **kw)

    def post(self, target, **kw):
        return self._retry_request(self._s.post, target, **kw)
