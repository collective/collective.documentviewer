from collective.documentviewer.settings import GlobalSettings
from zope.event import notify
from Products.Archetypes.event import ObjectInitializedEvent
from tempfile import mkdtemp

import unittest2 as unittest

from collective.documentviewer.settings import Settings
from collective.documentviewer import storage
from collective.documentviewer.tests import BaseTest
from collective.documentviewer.settings import STORAGE_VERSION
from os.path import join


class StorageTest(BaseTest):

    def test_retrieve_correct_resource_location_old_storage(self):
        gsettings = GlobalSettings(self.portal)
        _dir = mkdtemp()
        gsettings.storage_location = _dir
        fi = self.createFile('test.pdf')
        settings = Settings(fi)
        del settings._metadata['storage_version']
        self.assertEquals(storage.getResourceDirectory(obj=fi),
                          join(_dir, fi.UID()))

    def test_set_storage_version(self):
        gsettings = GlobalSettings(self.portal)
        _dir = mkdtemp()
        gsettings.storage_location = _dir
        fi = self.createFile('test.pdf')
        settings = Settings(fi)
        self.assertEquals(settings.storage_version,
                          STORAGE_VERSION)

    def test_retrieve_correct_resource_location_new_storage(self):
        gsettings = GlobalSettings(self.portal)
        _dir = mkdtemp()
        gsettings.storage_location = _dir
        fi = self.createFile('test.pdf')
        notify(ObjectInitializedEvent(fi))
        uid = fi.UID()
        self.assertEquals(storage.getResourceDirectory(obj=fi),
                          join(_dir, uid[0], uid[1], uid))

    def test_get_correct_rel_url_for_old_storage(self):
        fi = self.createFile('test.pdf')
        settings = Settings(fi)
        del settings._metadata['storage_version']
        uid = fi.UID()
        self.assertEquals(storage.getResourceRelURL(obj=fi),
                          '@@dvpdffiles/%s' % uid)

    def test_get_correct_rel_url_for_new_storage(self):
        fi = self.createFile('test.pdf')
        uid = fi.UID()
        self.assertEquals(storage.getResourceRelURL(obj=fi),
                          '@@dvpdffiles/%s/%s/%s' % (uid[0], uid[1], uid))

    def test_get_correct_rel_url_for_new_storage_with_resource_url(self):
        fi = self.createFile('test.pdf')
        gsettings = GlobalSettings(self.portal)
        gsettings.override_base_resource_url = 'http://foobar.com'
        uid = fi.UID()
        self.assertEquals(storage.getResourceRelURL(obj=fi),
                          '%s/%s/%s' % (uid[0], uid[1], uid))

    def test_get_correct_rel_url_for_old_storage_with_resource_url(self):
        fi = self.createFile('test.pdf')
        settings = Settings(fi)
        gsettings = GlobalSettings(self.portal)
        gsettings.override_base_resource_url = 'http://foobar.com'
        del settings._metadata['storage_version']
        uid = fi.UID()
        self.assertEquals(storage.getResourceRelURL(obj=fi),
                          '%s' % uid)


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)
