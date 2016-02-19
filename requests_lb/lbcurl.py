from .requests_lb import RequestsLB

import os
import sys
import logging
import argparse

try:
    from urllib.parse import urlparse
    from urllib.parse import parse_qs
    out_buffer = sys.stdout.buffer
except ImportError:
    from urlparse import urlparse
    from urlparse import parse_qs
    out_buffer = sys.stdout

def header_tuple(string):
    parts = string.split(':', 1)

    if len(parts) == 1:
        raise argparse.ArgumentTypeError("Header must contain ':'")

    return (parts[0].strip(), parts[1].strip())


parser = argparse.ArgumentParser()
parser.add_argument("target", metavar="<url>", help="Target URL")
parser.add_argument("-d", dest="data",
                    metavar="<data>", help="Send Data (implies POST)")
parser.add_argument("-X", dest="method",
                    metavar="<method>", help="Method to use", default=None)
parser.add_argument("--debug", dest="debug",
                    action="store_const", const=True,
                    help="Enable debugging", default=False)
parser.add_argument("-H", dest="headers",
                    metavar="<Header>", help="Add header",
                    action="append", default=list(), type=header_tuple)


def config_logging(ns):
    if ns.debug:
        logging.basicConfig(level='DEBUG')


def entry():
    ns = parser.parse_args()
    config_logging(ns)

    url = urlparse(ns.target)
    req = RequestsLB(url.netloc, protocol=url.scheme)

    kw = dict()

    kw['headers'] = dict(ns.headers)

    if ns.data is not None:
        if ns.method is None:
            ns.method = 'POST'

        kw['data'] = ns.data
    else:
        if ns.method is None:
            ns.method = 'GET'

    kw['params'] = parse_qs(url.query)

    response = req.request(ns.method, url.path, **kw)

    if ns.debug:
        sys.stderr.write(
            "< {} {}".format(response.status_code, response.reason) +
            os.linesep)

        for (key, value) in response.headers.items():
            sys.stderr.write("< {}: {}".format(key, value) + os.linesep)

    out_buffer.write(response.content)
