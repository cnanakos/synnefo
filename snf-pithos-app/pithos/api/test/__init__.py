#!/usr/bin/env python
#coding=utf8

# Copyright 2011-2013 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

from urlparse import urlunsplit, urlsplit
from xml.dom import minidom

from snf_django.utils.testing import with_settings, astakos_user

from pithos.backends.random_word import get_random_word
from pithos.api import settings as pithos_settings

from django.test import TestCase
from django.utils.http import urlencode
from django.conf import settings

import django.utils.simplejson as json

import re
import random
import threading
import functools

pithos_test_settings = functools.partial(with_settings, pithos_settings)

DATE_FORMATS = ["%a %b %d %H:%M:%S %Y",
                "%A, %d-%b-%y %H:%M:%S GMT",
                "%a, %d %b %Y %H:%M:%S GMT"]

o_names = ['kate.jpg',
           'kate_beckinsale.jpg',
           'How To Win Friends And Influence People.pdf',
           'moms_birthday.jpg',
           'poodle_strut.mov',
           'Disturbed - Down With The Sickness.mp3',
           'army_of_darkness.avi',
           'the_mad.avi',
           'photos/animals/dogs/poodle.jpg',
           'photos/animals/dogs/terrier.jpg',
           'photos/animals/cats/persian.jpg',
           'photos/animals/cats/siamese.jpg',
           'photos/plants/fern.jpg',
           'photos/plants/rose.jpg',
           'photos/me.jpg']

details = {'container': ('name', 'count', 'bytes', 'last_modified',
                         'x_container_policy'),
           'object': ('name', 'hash', 'bytes', 'content_type',
                      'content_encoding', 'last_modified',)}

return_codes = (400, 401, 403, 404, 503)


class PithosAPITest(TestCase):
    #TODO unauthorized request
    def setUp(self):
        pithos_settings.BACKEND_DB_MODULE = 'pithos.backends.lib.sqlalchemy'
        pithos_settings.BACKEND_DB_CONNECTION = construct_db_connection()
        pithos_settings.BACKEND_POOL_SIZE = 1
        self.user = 'user'

    def tearDown(self):
        #delete additionally created metadata
        meta = self.get_account_meta()
        self.delete_account_meta(meta)

        #delete additionally created groups
        groups = self.get_account_groups()
        self.delete_account_groups(groups)

        self._clean_account()

    def head(self, url, user='user', *args, **kwargs):
        with astakos_user(user):
            response = self.client.head(url, *args, **kwargs)
        return response

    def get(self, url, user='user', *args, **kwargs):
        with astakos_user(user):
            response = self.client.get(url, *args, **kwargs)
        return response

    def delete(self, url, user='user', *args, **kwargs):
        with astakos_user(user):
            response = self.client.delete(url, *args, **kwargs)
        return response

    def post(self, url, user='user', *args, **kwargs):
        with astakos_user(user):
            kwargs.setdefault('content_type', 'application/octet-stream')
            response = self.client.post(url, *args, **kwargs)
        return response

    def put(self, url, user='user', *args, **kwargs):
        with astakos_user(user):
            kwargs.setdefault('content_type', 'application/octet-stream')
            response = self.client.put(url, *args, **kwargs)
        return response

    def _clean_account(self):
        for c in self.list_containers():
            self.delete_container_content(c['name'])
            self.delete_container(c['name'])

    def update_account_meta(self, meta):
        kwargs = dict(
            ('HTTP_X_ACCOUNT_META_%s' % k, str(v)) for k, v in meta.items())
        r = self.post('/v1/%s?update=' % self.user, **kwargs)
        self.assertEqual(r.status_code, 202)
        account_meta = self.get_account_meta()
        (self.assertTrue('X-Account-Meta-%s' % k in account_meta) for
            k in meta.keys())
        (self.assertEqual(account_meta['X-Account-Meta-%s' % k], v) for
            k, v in meta.items())

    def reset_account_meta(self, meta):
        kwargs = dict(
            ('HTTP_X_ACCOUNT_META_%s' % k, str(v)) for k, v in meta.items())
        r = self.post('/v1/%s' % self.user, **kwargs)
        self.assertEqual(r.status_code, 202)
        account_meta = self.get_account_meta()
        (self.assertTrue('X-Account-Meta-%s' % k in account_meta) for
            k in meta.keys())
        (self.assertEqual(account_meta['X-Account-Meta-%s' % k], v) for
            k, v in meta.items())

    def delete_account_meta(self, meta):
        transform = lambda k: 'HTTP_%s' % k.replace('-', '_').upper()
        kwargs = dict((transform(k), '') for k, v in meta.items())
        r = self.post('/v1/%s?update=' % self.user, **kwargs)
        self.assertEqual(r.status_code, 202)
        account_meta = self.get_account_meta()
        (self.assertTrue('X-Account-Meta-%s' % k not in account_meta) for
            k in meta.keys())
        return r

    def delete_account_groups(self, groups):
        r = self.post('/v1/%s?update=' % self.user, **groups)
        self.assertEqual(r.status_code, 202)
        return r

    def get_account_info(self, until=None):
        url = '/v1/%s' % self.user
        if until is not None:
            parts = list(urlsplit(url))
            parts[3] = urlencode({
                'until': until
            })
            url = urlunsplit(parts)
        r = self.head(url)
        self.assertEqual(r.status_code, 204)
        return r

    def get_account_meta(self, until=None):
        r = self.get_account_info(until=until)
        headers = dict(r._headers.values())
        map(headers.pop,
            [k for k in headers.keys()
                if not k.startswith('X-Account-Meta-')])
        return headers

    def get_account_groups(self, until=None):
        r = self.get_account_info(until=until)
        headers = dict(r._headers.values())
        map(headers.pop,
            [k for k in headers.keys()
                if not k.startswith('X-Account-Group-')])
        return headers

    def list_containers(self, format='json', headers={}, **params):
        url = '/v1/%s' % self.user
        parts = list(urlsplit(url))
        params['format'] = format
        parts[3] = urlencode(params)
        url = urlunsplit(parts)
        _headers = dict(('HTTP_%s' % k.upper(), str(v))
                        for k, v in headers.items())
        r = self.get(url, **_headers)

        if format is None:
            containers = r.content.split('\n')
            if '' in containers:
                containers.remove('')
            return containers
        elif format == 'json':
            try:
                containers = json.loads(r.content)
            except:
                self.fail('json format expected')
            return containers
        elif format == 'xml':
            return minidom.parseString(r.content)

    def delete_container_content(self, cname):
        r = self.delete('/v1/%s/%s?delimiter=/' % (self.user, cname))
        self.assertEqual(r.status_code, 204)
        return r

    def delete_container(self, cname):
        r = self.delete('/v1/%s/%s' % (self.user, cname))
        self.assertEqual(r.status_code, 204)
        return r

    def create_container(self, cname):
        r = self.put('/v1/%s/%s' % (self.user, cname), data='')
        self.assertTrue(r.status_code in (202, 201))
        return r

    def upload_object(self, cname, oname=None, **meta):
        oname = oname or get_random_word(8)
        data = get_random_word(length=random.randint(1, 1024))
        headers = dict(('HTTP_X_OBJECT_META_%s' % k.upper(), v)
                       for k, v in meta.iteritems())
        r = self.put('/v1/%s/%s/%s' % (
            self.user, cname, oname), data=data, **headers)
        self.assertEqual(r.status_code, 201)
        return oname, data, r

    def create_folder(self, cname, oname=get_random_word(8), **headers):
        r = self.put('/v1/%s/%s/%s' % (
            self.user, cname, oname), data='',
            content_type='application/directory',
            **headers)
        self.assertEqual(r.status_code, 201)
        return oname, r

    def list_objects(self, cname):
        r = self.get('/v1/%s/%s?format=json' % (self.user, cname))
        self.assertTrue(r.status_code in (200, 204))
        try:
            objects = json.loads(r.content)
        except:
            self.fail('json format expected')
        return objects

    def assert_status(self, status, codes):
        l = [elem for elem in return_codes]
        if isinstance(codes, list):
            l.extend(codes)
        else:
            l.append(codes)
        self.assertTrue(status in l)

    def assert_extended(self, data, format, type, size=10000):
        if format == 'xml':
            self._assert_xml(data, type, size)
        elif format == 'json':
            self._assert_json(data, type, size)

    def _assert_json(self, data, type, size):
        convert = lambda s: s.lower()
        info = [convert(elem) for elem in details[type]]
        self.assertTrue(len(data) <= size)
        for item in info:
            for i in data:
                if 'subdir' in i.keys():
                    continue
                self.assertTrue(item in i.keys())

    def _assert_xml(self, data, type, size):
        convert = lambda s: s.lower()
        info = [convert(elem) for elem in details[type]]
        try:
            info.remove('content_encoding')
        except ValueError:
            pass
        xml = data
        entities = xml.getElementsByTagName(type)
        self.assertTrue(len(entities) <= size)
        for e in entities:
            for item in info:
                self.assertTrue(e.getElementsByTagName(item))


class AssertMappingInvariant(object):
    def __init__(self, callable, *args, **kwargs):
        self.callable = callable
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        self.map = self.callable(*self.args, **self.kwargs)
        return self.map

    def __exit__(self, type, value, tb):
        map = self.callable(*self.args, **self.kwargs)
        for k, v in self.map.items():
            if is_date(v):
                continue

            assert(k in map), '%s not in map' % k
            assert v == map[k]

django_sqlalchemy_engines = {
    'django.db.backends.postgresql_psycopg2': 'postgresql+psycopg2',
    'django.db.backends.postgresql': 'postgresql',
    'django.db.backends.mysql': '',
    'django.db.backends.sqlite3': 'mssql',
    'django.db.backends.oracle': 'oracle'}


def construct_db_connection():
    """Convert the django default database to an sqlalchemy connection
       string"""
    db = settings.DATABASES['default']
    if db['ENGINE'] == 'django.db.backends.sqlite3':
        return 'sqlite://'
    else:
        d = dict(scheme=django_sqlalchemy_engines.get(db['ENGINE']),
                 user=db['USER'],
                 pwd=db['PASSWORD'],
                 host=db['HOST'].lower(),
                 port=int(db['PORT']) if db['PORT'] != '' else '',
                 name=db['NAME'])
        return '%(scheme)s://%(user)s:%(pwd)s@%(host)s:%(port)s/%(name)s' % d


def is_date(date):
    __D = r'(?P<day>\d{2})'
    __D2 = r'(?P<day>[ \d]\d)'
    __M = r'(?P<mon>\w{3})'
    __Y = r'(?P<year>\d{4})'
    __Y2 = r'(?P<year>\d{2})'
    __T = r'(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})'
    RFC1123_DATE = re.compile(r'^\w{3}, %s %s %s %s GMT$' % (
        __D, __M, __Y, __T))
    RFC850_DATE = re.compile(r'^\w{6,9}, %s-%s-%s %s GMT$' % (
        __D, __M, __Y2, __T))
    ASCTIME_DATE = re.compile(r'^\w{3} %s %s %s %s$' % (
        __M, __D2, __T, __Y))
    for regex in RFC1123_DATE, RFC850_DATE, ASCTIME_DATE:
        m = regex.match(date)
        if m is not None:
            return True
    return False


def strnextling(prefix):
    """Return the first unicode string
       greater than but not starting with given prefix.
       strnextling('hello') -> 'hellp'
    """
    if not prefix:
        ## all strings start with the null string,
        ## therefore we have to approximate strnextling('')
        ## with the last unicode character supported by python
        ## 0x10ffff for wide (32-bit unicode) python builds
        ## 0x00ffff for narrow (16-bit unicode) python builds
        ## We will not autodetect. 0xffff is safe enough.
        return unichr(0xffff)
    s = prefix[:-1]
    c = ord(prefix[-1])
    if c >= 0xffff:
        raise RuntimeError
    s += unichr(c + 1)
    return s


def test_concurrently(times=2):
    """
    Add this decorator to small pieces of code that you want to test
    concurrently to make sure they don't raise exceptions when run at the
    same time.  E.g., some Django views that do a SELECT and then a subsequent
    INSERT might fail when the INSERT assumes that the data has not changed
    since the SELECT.
    """
    def test_concurrently_decorator(test_func):
        def wrapper(*args, **kwargs):
            exceptions = []

            def call_test_func():
                try:
                    test_func(*args, **kwargs)
                except Exception, e:
                    exceptions.append(e)
                    raise

            threads = []
            for i in range(times):
                threads.append(threading.Thread())
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            if exceptions:
                raise Exception(
                    ('test_concurrently intercepted %s',
                     'exceptions: %s') % (len(exceptions), exceptions))
        return wrapper
    return test_concurrently_decorator
