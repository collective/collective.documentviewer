import unittest
from os import listdir
from os.path import exists, join
from tempfile import mkdtemp

from collective.documentviewer import storage
from collective.documentviewer.settings import (STORAGE_VERSION,
                                                GlobalSettings, Settings)
from collective.documentviewer.tests import BaseTest
from Products.CMFCore.utils import getToolByName
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent


class StorageTest(BaseTest):

    def test_retrieve_correct_resource_location_old_storage(self):
        gsettings = GlobalSettings(self.portal)
        _dir = mkdtemp()
        gsettings.storage_location = _dir
        fi = self.createFile('test.pdf')
        settings = Settings(fi)
        del settings._metadata['storage_version']
        self.assertEqual(storage.getResourceDirectory(obj=fi),
                         join(_dir, fi.UID()))

    def test_set_storage_version(self):
        gsettings = GlobalSettings(self.portal)
        _dir = mkdtemp()
        gsettings.storage_location = _dir
        fi = self.createFile('test.pdf')
        settings = Settings(fi)
        self.assertEqual(settings.storage_version,
                         STORAGE_VERSION)

    def test_retrieve_correct_resource_location_new_storage(self):
        gsettings = GlobalSettings(self.portal)
        _dir = mkdtemp()
        gsettings.storage_location = _dir
        fi = self.createFile('test.pdf')
        notify(ObjectModifiedEvent(fi))
        uid = fi.UID()
        self.assertEqual(storage.getResourceDirectory(obj=fi),
                         join(_dir, uid[0], uid[1], uid))

    def test_get_correct_rel_url_for_old_storage(self):
        fi = self.createFile('test.pdf')
        settings = Settings(fi)
        del settings._metadata['storage_version']
        uid = fi.UID()
        self.assertEqual(storage.getResourceRelURL(obj=fi),
                         '@@dvpdffiles/%s' % uid)

    def test_get_correct_rel_url_for_new_storage(self):
        fi = self.createFile('test.pdf')
        uid = fi.UID()
        self.assertEqual(storage.getResourceRelURL(obj=fi),
                         '@@dvpdffiles/%s/%s/%s' % (uid[0], uid[1], uid))

    def test_get_correct_rel_url_for_new_storage_with_resource_url(self):
        fi = self.createFile('test.pdf')
        gsettings = GlobalSettings(self.portal)
        gsettings.override_base_resource_url = 'http://foobar.com'
        uid = fi.UID()
        self.assertEqual(storage.getResourceRelURL(obj=fi),
                         '%s/%s/%s' % (uid[0], uid[1], uid))

    def test_get_correct_rel_url_for_old_storage_with_resource_url(self):
        fi = self.createFile('test.pdf')
        settings = Settings(fi)
        gsettings = GlobalSettings(self.portal)
        gsettings.override_base_resource_url = 'http://foobar.com'
        del settings._metadata['storage_version']
        uid = fi.UID()
        self.assertEqual(storage.getResourceRelURL(obj=fi),
                         '%s' % uid)

    def test_storage_obsfucates_dir(self):
        gsettings = GlobalSettings(self.portal)
        _dir = mkdtemp()
        gsettings.storage_location = _dir
        gsettings.storage_type = 'File'
        gsettings.storage_obfuscate = True
        fi = self.createFile('test.pdf')
        uid = fi.UID()
        fi.reindexObject()
        notify(ObjectModifiedEvent(fi))
        settings = Settings(fi)
        self.assertTrue(
            exists(join(_dir, uid[0], uid[1], uid,
                        settings.obfuscate_secret)))
        self.assertTrue(
            len(listdir(join(_dir, uid[0], uid[1], uid,
                             settings.obfuscate_secret))) > 3)

    def test_storage_removes_obfuscation(self):
        gsettings = GlobalSettings(self.portal)
        _dir = mkdtemp()
        gsettings.storage_location = _dir
        gsettings.storage_type = 'File'
        gsettings.storage_obfuscate = True
        fi = self.createFile('test.pdf')
        uid = fi.UID()
        fi.reindexObject()
        notify(ObjectModifiedEvent(fi))
        settings = Settings(fi)
        self.assertTrue(
            exists(join(_dir, uid[0], uid[1], uid,
                        settings.obfuscate_secret)))
        self.assertTrue(
            len(listdir(join(_dir, uid[0], uid[1], uid,
                             settings.obfuscate_secret))) > 3)
        # publish now
        workflowTool = getToolByName(fi, 'portal_workflow')
        workflowTool.doActionFor(fi, 'publish')
        self.assertTrue(
            not exists(join(_dir, uid[0], uid[1], uid,
                            settings.obfuscate_secret)))

    def test_publish_unpublish_again_works_with_obfuscation(self):
        gsettings = GlobalSettings(self.portal)
        _dir = mkdtemp()
        gsettings.storage_location = _dir
        gsettings.storage_type = 'File'
        gsettings.storage_obfuscate = True
        fi = self.createFile('test.pdf')
        uid = fi.UID()
        settings = Settings(fi)
        self.assertTrue(
            exists(join(_dir, uid[0], uid[1], uid,
                        settings.obfuscate_secret)))
        self.assertTrue(
            len(listdir(join(_dir, uid[0], uid[1], uid,
                             settings.obfuscate_secret))) > 3)
        # publish now
        workflowTool = getToolByName(fi, 'portal_workflow')
        workflowTool.doActionFor(fi, 'publish')
        self.assertTrue(
            not exists(join(_dir, uid[0], uid[1], uid,
                            settings.obfuscate_secret)))
        workflowTool.doActionFor(fi, 'retract')
        self.assertTrue(
            exists(join(_dir, uid[0], uid[1], uid,
                        settings.obfuscate_secret)))
        self.assertTrue(
            len(listdir(join(_dir, uid[0], uid[1], uid,
                             settings.obfuscate_secret))) > 3)


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)
