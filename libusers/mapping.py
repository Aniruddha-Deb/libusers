import requests
from html.parser import HTMLParser
from os import environ
from datetime import datetime, timedelta
import pickle
import os

UPDATE_URL = "http://ldapweb.iitd.ac.in/LDAP/iitd/hpcusers.shtml"
UPDATE_FILE = environ['HOME'] + '/.local/share/userlib/mapping.txt'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

def safe_open(path, ops):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return open(path, ops)

class Mapping:

    def __init__(self, map):
        self.map = map
        self.upd_time = datetime.now()
    
    def serialize(self, file):
        with safe_open(file, 'wb') as outfile:
            pickle.dump(self, outfile)

    @classmethod
    def deserialize(cls, file):
        with open(file, 'rb') as infile:
            return pickle.load(infile)

    def __str__(self):
        s = ''
        mlen = max([len(k) for k in self.map])
        for k, v in self.map.items():
            s += f'{k:{mlen}} {v}\n'
        s += f'\nUpdated on {self.upd_time.strftime(DATE_FORMAT)}\n'
        return s
        

# simple state-machine based mapping parser
class MappingParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.in_row = False
        self.in_kerberos = False
        self.kerberos = None
        self.in_name = False

        self.mapping = {}

    def feed(self, data):
        super().feed(data)
        mapping = Mapping(self.mapping)
        self.mapping = {}
        return mapping

    def handle_starttag(self, tag, attrs):
        if (not self.in_row) and tag.lower() == 'tr':
            self.in_row = True
        elif len(attrs) > 0 and self.in_row and tag.lower() == 'td':
            # kerberos is left aligned
            self.in_kerberos = True
        elif (self.kerberos is not None) and self.in_row and tag.lower() == 'td':
            self.in_name = True

    def handle_endtag(self, tag):
        if self.in_row and tag.lower() == 'tr':
            self.in_row = False
        elif self.in_kerberos and tag.lower() == 'td':
            self.in_kerberos = False
        elif self.in_name and tag.lower() == 'td':
            self.in_name = False

    def handle_data(self, data):
        if self.in_row:
            if self.in_kerberos:
                self.kerberos = data
            elif self.in_name:
                name = data
                split_name = data.split(' ')
                if len(split_name) > 3:
                    # southie names do be big
                    name = split_name[0] + ' ' + split_name[1] + ' ' + split_name[-1]
                self.mapping[self.kerberos] = name
                self.kerberos = None

def get_updated():

    mp = MappingParser()
    raw_mapping = requests.get(UPDATE_URL).text
    mapping = mp.feed(raw_mapping)
    mapping.serialize(UPDATE_FILE)
    print('Updated mapping')

    return mapping

def get_lazy_updated(delta=timedelta(days=7)):

    if not os.path.exists(UPDATE_FILE):
        return get_updated()

    mapping = Mapping.deserialize(UPDATE_FILE)
    if (datetime.now() - mapping.upd_time > delta):
        print('Mapping has not been updated in a week, updating now')
        return get_updated()

    return mapping

if __name__ == '__main__':
    mapping = get_updated()
    print(mapping)


