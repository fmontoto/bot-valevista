import logging
import requests

logger = logging.getLogger(__name__)

class Web(object):
    URL = "http://www.empresas.bancochile.cl/cgi-bin/cgi_cpf?rut1=60910000&dv1=1&canal=BCW&tipo=2&BEN_DIAS=90&mediopago=99&rut2=%s&dv2=%s"
    def __init__(self, rut, digito):
        self.rut = rut;
        self.digito = digit
        self.raw_page = "";

    def download(self):
        try:
            r = requests.get(self.URL % (self.rut, self.digito))
        except requests.exceptions.RequestException e:
            logger
        if(r.status_code != 200):
            logger.warn("Couldn't get the page, error %s:%s" % (r.status_code,
                                                                r.reason))

        self.raw_page = r.text

    """ Testing purposes."""
    def load_page(self, path):
        with open(path) as f:
            self.raw_page = f.read()
