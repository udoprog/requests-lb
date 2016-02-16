import unittest

from unittest.mock import Mock

from requests_lb.requests_lb import RequestsLB

class RequestsLBTest(unittest.TestCase):
    def setUp(self):
        self.time = Mock()
        self.srv = Mock()
        self.sample = Mock()
        self.lb = RequestsLB(
            'foo', time_provider=self.time, srv_provider=lambda **kw: self.srv,
            sample_provider=self.sample)

    def test_filter_bad_hosts(self):
        self.lb._srv_bad_hosts = dict(a=None, b=None)
        self.assertEquals(set(['c']), self.lb._srv_filter(['b', 'c']))

    def test_srv_is_expired(self):
        self.lb._srv_update_timeout = 30

        # no update, always expired
        self.assertTrue(self.lb._srv_is_expired())

        self.time.return_value = 29
        self.lb._srv_last_update = 0
        self.assertFalse(self.lb._srv_is_expired())

        self.time.return_value = 30
        self.assertTrue(self.lb._srv_is_expired())

    def test_next_host(self):
        self.lb._srv_is_expired = Mock(return_value=True)

        self.srv.return_value = [('a', 1234), ('b', 1234)]
        self.sample.return_value = ('b', 1234)

        self.assertEquals(None, self.lb._srv_host)
        self.assertEquals(set(), self.lb._srv_hosts)

        self.assertEquals(('b', 1234), self.lb._srv_next_host())

        self.assertEquals(('b', 1234), self.lb._srv_host)
        self.assertEquals(set([('a', 1234), ('b', 1234)]), self.lb._srv_hosts)
