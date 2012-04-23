from tempfile import mkdtemp
from collective.documentviewer.settings import GlobalSettings
from zope.event import notify
from Products.Archetypes.event import ObjectInitializedEvent

import unittest2 as unittest
from collective.documentviewer.convert import Converter
from collective.documentviewer.settings import Settings
from collective.documentviewer.tests import BaseTest
from collective.documentviewer import storage
from os import listdir
import shutil
from os.path import join


class ConvertTest(BaseTest):

    def test_converts(self):
        fi = self.createFile('test.pdf')
        settings = Settings(fi)
        self.assertEqual(settings.successfully_converted, None)
        notify(ObjectInitializedEvent(fi))
        self.assertEqual(settings.successfully_converted, True)
        self.assertEqual(settings.num_pages, 1)

    def test_auto_assigns_view(self):
        fi = self.createFile('test.pdf')
        gsettings = GlobalSettings(self.portal)
        gsettings.auto_select_layout = True
        notify(ObjectInitializedEvent(fi))
        self.assertEqual(fi.getLayout(), 'documentviewer')

    def test_not_auto_assigns_view(self):
        fi = self.createFile('test.pdf')
        gsettings = GlobalSettings(self.portal)
        gsettings.auto_select_layout = False
        notify(ObjectInitializedEvent(fi))
        self.assertTrue(fi.getLayout() != 'documentviewer')

    def test_auto_convert_word(self):
        fi = self.createFile('test.doc')
        gsettings = GlobalSettings(self.portal)
        gsettings.auto_select_layout = True
        gsettings.auto_layout_file_types = ['word']
        notify(ObjectInitializedEvent(fi))
        settings = Settings(fi)
        self.assertEqual(settings.successfully_converted, True)
        self.assertEqual(settings.num_pages, 2)

    def test_auto_convert_powerpoint(self):
        fi = self.createFile('test.odp')
        gsettings = GlobalSettings(self.portal)
        gsettings.auto_select_layout = True
        gsettings.auto_layout_file_types = ['ppt']
        notify(ObjectInitializedEvent(fi))
        settings = Settings(fi)
        self.assertEqual(settings.successfully_converted, True)
        self.assertEqual(settings.num_pages, 1)

    def test_sets_filehash(self):
        fi = self.createFile('test.odp')
        gsettings = GlobalSettings(self.portal)
        gsettings.auto_select_layout = True
        gsettings.auto_layout_file_types = ['ppt']
        notify(ObjectInitializedEvent(fi))
        settings = Settings(fi)
        self.assertTrue(settings.filehash is not None)

    def test_sets_can_not_convert_after_conversion(self):
        fi = self.createFile('test.odp')
        gsettings = GlobalSettings(self.portal)
        gsettings.auto_select_layout = True
        gsettings.auto_layout_file_types = ['ppt']
        notify(ObjectInitializedEvent(fi))
        converter = Converter(fi)
        self.assertTrue(not converter.can_convert)

    def test_saves_with_file_storage(self):
        fi = self.createFile('test.odp')
        gsettings = GlobalSettings(self.portal)
        gsettings.auto_select_layout = True
        gsettings.auto_layout_file_types = ['ppt']
        gsettings.storage_type = 'File'
        _dir = mkdtemp()
        gsettings.storage_location = _dir
        notify(ObjectInitializedEvent(fi))

        fi_dir = storage.getResourceDirectory(obj=fi)
        self.assertEqual(len(listdir(fi_dir)), 4)
        self.assertEqual(len(listdir(join(fi_dir, 'normal'))), 1)
        self.assertEqual(len(listdir(join(fi_dir, 'small'))), 1)
        self.assertEqual(len(listdir(join(fi_dir, 'large'))), 1)
        self.assertEqual(len(listdir(join(fi_dir, 'text'))), 1)
        shutil.rmtree(fi_dir)


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)
