import unittest
from os.path import join
from tempfile import mkdtemp

from collective.documentviewer.browser.traverse import BlobFileWrapper
from collective.documentviewer.settings import GlobalSettings, Settings
from collective.documentviewer.tests import BaseTest
from zExceptions import NotFound
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent


class PDFResourceTraverseTest(BaseTest):

    def test_filesystem_storage_works(self):
        gsettings = GlobalSettings(self.portal)
        _dir = mkdtemp()
        gsettings.storage_location = _dir
        gsettings.storage_type = 'File'
        fi = self.createFile('test.pdf')
        notify(ObjectModifiedEvent(fi))
        uid = fi.UID()
        fi.reindexObject()  # for pc
        fiobj = self.portal.unrestrictedTraverse(
            '@@dvpdffiles/%s/%s/%s/small/dump_1.gif' % (
                uid[0], uid[1], uid))
        self.assertEqual(
            fiobj.context.path,
            join(_dir, uid[0], uid[1], uid, 'small', 'dump_1.gif'))
        fiobj = self.portal.unrestrictedTraverse(
            '@@dvpdffiles/%s/%s/%s/normal/dump_1.gif' % (
                uid[0], uid[1], uid))
        self.assertEqual(
            fiobj.context.path,
            join(_dir, uid[0], uid[1], uid, 'normal', 'dump_1.gif'))
        fiobj = self.portal.unrestrictedTraverse(
            '@@dvpdffiles/%s/%s/%s/large/dump_1.gif' % (
                uid[0], uid[1], uid))
        self.assertEqual(
            fiobj.context.path,
            join(_dir, uid[0], uid[1], uid, 'large', 'dump_1.gif'))
        fiobj = self.portal.unrestrictedTraverse(
            '@@dvpdffiles/%s/%s/%s/text/dump_1.txt' % (
                uid[0], uid[1], uid))
        self.assertEqual(
            fiobj.context.path,
            join(_dir, uid[0], uid[1], uid, 'text', 'dump_1.txt'))

    def test_filesystem_old_storage_works(self):
        gsettings = GlobalSettings(self.portal)
        _dir = mkdtemp()
        gsettings.storage_location = _dir
        gsettings.storage_type = 'File'
        fi = self.createFile('test.pdf')
        uid = fi.UID()
        fiobj = self.portal.unrestrictedTraverse(
            '@@dvpdffiles/{}/{}/{}/small/dump_1.gif'.format(
                uid[0], uid[1], uid))
        self.assertEqual(
            fiobj.context.path,
            join(_dir, uid[0], uid[1], uid, 'small', 'dump_1.gif'))

    def test_filesystem_missing_gives_404(self):
        gsettings = GlobalSettings(self.portal)
        _dir = mkdtemp()
        gsettings.storage_location = _dir
        gsettings.storage_type = 'File'
        fi = self.createFile('test.pdf')
        notify(ObjectModifiedEvent(fi))
        uid = fi.UID()
        self.assertRaises(
            KeyError,
            self.portal.unrestrictedTraverse,
            '@@dvpdffiles/%s/%s/%s/small/foobar.gif' % (
                uid[0], uid[1], uid))

    def test_blob_old_storage_works(self):
        gsettings = GlobalSettings(self.portal)
        gsettings.storage_type = 'Blob'
        fi = self.createFile('test.pdf')
        settings = Settings(fi)
        del settings._metadata['storage_version']
        notify(ObjectModifiedEvent(fi))
        uid = fi.UID()
        fi.reindexObject()  # for pc
        req = self.request
        files = self.portal.unrestrictedTraverse('@@dvpdffiles')
        blobtraverser = files.publishTraverse(req, uid)
        blobtraverser = blobtraverser.publishTraverse(req, 'small')
        blobtraverser = blobtraverser.publishTraverse(req, 'dump_1.gif')
        self.assertTrue(isinstance(blobtraverser, BlobFileWrapper))

    def test_blob_new_storage_works(self):
        gsettings = GlobalSettings(self.portal)
        gsettings.storage_type = 'Blob'
        fi = self.createFile('test.pdf')
        notify(ObjectModifiedEvent(fi))
        uid = fi.UID()
        fi.reindexObject()  # for pc
        req = self.request
        files = self.portal.unrestrictedTraverse('@@dvpdffiles')
        files = files.publishTraverse(req, uid[0])
        files = files.publishTraverse(req, uid[1])
        blobtraverser = files.publishTraverse(req, uid)
        blobtraverser = blobtraverser.publishTraverse(req, 'small')
        blobtraverser = blobtraverser.publishTraverse(req, 'dump_1.gif')
        self.assertTrue(isinstance(blobtraverser, BlobFileWrapper))

    def test_extra_paths_404s(self):
        files = self.portal.unrestrictedTraverse('@@dvpdffiles')
        req = self.request
        files = files.publishTraverse(req, '1')
        files = files.publishTraverse(req, '2')
        self.assertRaises(NotFound, files.publishTraverse, req, '3df')
        files = self.portal.unrestrictedTraverse('@@dvpdffiles')
        files = files.publishTraverse(req, '1')
        self.assertRaises(NotFound, files.publishTraverse, req, '332')


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)
