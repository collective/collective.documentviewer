from collective.documentviewer.settings import GlobalSettings
from tempfile import mkdtemp
from zope.annotation.interfaces import IAnnotations
from zope.event import notify
from Products.Archetypes.event import ObjectInitializedEvent

import unittest2 as unittest

from collective.documentviewer.tests import BaseTest
from os.path import exists
from os.path import join


class MigrateTest(BaseTest):

    def test_migrate_page_turner_on_convert(self):
        fi = self.createFile('test.pdf')
        fi.layout = 'page-turner'
        annotations = IAnnotations(fi)
        metadata = {'foo': 'bar'}
        annotations['wc.pageturner'] = metadata
        notify(ObjectInitializedEvent(fi))
        annotations = IAnnotations(fi)
        self.assertTrue('wc.pageturner' not in annotations)
        self.assertEquals(fi.layout, 'documentviewer')

    def test_migrate_pdfpal_on_convert(self):
        fi = self.createFile('test.pdf')
        fi.layout = 'page-turner'
        annotations = IAnnotations(fi)
        metadata = {'foo': 'bar'}
        annotations['wc.pageturner'] = metadata
        notify(ObjectInitializedEvent(fi))
        annotations = IAnnotations(fi)
        self.assertTrue('wc.pageturner' not in annotations)
        self.assertEquals(fi.layout, 'documentviewer')

    def test_cleanup_file_storage(self):
        gsettings = GlobalSettings(self.portal)
        _dir = mkdtemp()
        gsettings.storage_location = _dir
        gsettings.storage_type = 'File'
        fi = self.createFile('test.pdf')
        uid = fi.UID()
        notify(ObjectInitializedEvent(fi))
        self.portal.manage_delObjects([fi.getId()])
        self.assertTrue(exists(join(_dir, uid[0], uid[1], uid)))
        self.portal.unrestrictedTraverse('@@dvcleanup-filestorage')()
        self.assertTrue(not exists(join(_dir, uid[0], uid[1], uid)))

    def test_cleanup_file_storage_does_not_delete_good_files(self):
        gsettings = GlobalSettings(self.portal)
        _dir = mkdtemp()
        gsettings.storage_location = _dir
        gsettings.storage_type = 'File'
        fi = self.createFile('test.pdf')
        uid = fi.UID()
        fi.reindexObject()
        notify(ObjectInitializedEvent(fi))
        self.assertTrue(exists(join(_dir, uid[0], uid[1], uid)))
        self.portal.unrestrictedTraverse('@@dvcleanup-filestorage')()
        self.assertTrue(exists(join(_dir, uid[0], uid[1], uid)))


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)
