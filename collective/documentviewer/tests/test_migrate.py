import unittest
from os import listdir
from os.path import exists, join
from tempfile import mkdtemp

from collective.documentviewer import storage
from collective.documentviewer.settings import (STORAGE_VERSION,
                                                GlobalSettings, Settings)
from collective.documentviewer.tests import BaseTest
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent


class MigrateTest(BaseTest):

    def test_cleanup_file_storage(self):
        gsettings = GlobalSettings(self.portal)
        _dir = mkdtemp()
        gsettings.storage_location = _dir
        gsettings.storage_type = 'File'
        fi = self.createFile('test.pdf')
        uid = fi.UID()
        self.assertTrue(exists(join(_dir, uid[0], uid[1], uid)))
        self.portal.manage_delObjects([fi.getId()])
        self.assertTrue(not exists(join(_dir, uid[0], uid[1], uid)))

    def test_cleanup_file_storage_does_not_delete_good_files(self):
        gsettings = GlobalSettings(self.portal)
        _dir = mkdtemp()
        gsettings.storage_location = _dir
        gsettings.storage_type = 'File'
        fi = self.createFile('test.pdf')
        uid = fi.UID()
        fi.reindexObject()
        notify(ObjectModifiedEvent(fi))
        self.assertTrue(exists(join(_dir, uid[0], uid[1], uid)))
        self.portal.unrestrictedTraverse('@@dvcleanup-filestorage')()
        self.assertTrue(exists(join(_dir, uid[0], uid[1], uid)))

    def test_migrate_old_storage(self):
        gsettings = GlobalSettings(self.portal)
        _dir = mkdtemp()
        gsettings.storage_location = _dir
        gsettings.storage_type = 'File'
        fi = self.createFile('test.pdf')
        settings = Settings(fi)
        del settings._metadata['storage_version']
        fi.reindexObject()
        notify(ObjectModifiedEvent(fi))
        self.assertEqual(settings.storage_version, 1)
        old_path = storage.getResourceDirectory(obj=fi)
        self.assertTrue(exists(old_path))
        from collective.documentviewer.upgrades import migrate_old_storage
        migrate_old_storage(self.portal)
        self.assertTrue(not exists(old_path))
        self.assertEqual(settings.storage_version, STORAGE_VERSION)
        new_path = storage.getResourceDirectory(obj=fi)
        self.assertTrue(exists(new_path))
        self.assertEqual(len(listdir(new_path)), 6)


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)
