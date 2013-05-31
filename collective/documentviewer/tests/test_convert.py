from tempfile import mkdtemp
from DateTime import DateTime
from collective.documentviewer.settings import GlobalSettings
from zope.annotation import IAnnotations
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

    def test_indexation_enabled(self):
        fi = self.createFile('test.pdf')
        gsettings = GlobalSettings(self.portal)
        # indexation is enabled by default
        self.assertEquals(gsettings.enable_indexation, True)
        notify(ObjectInitializedEvent(fi))
        # make sure conversion was successfull
        self.failUnless(self._isSuccessfullyConverted(fi))
        annotations = IAnnotations(fi)['collective.documentviewer']
        self.failUnless(annotations['catalog'] is not None)
        # we have relevant informations in the catalog
        self.failUnless('software' in annotations['catalog']['text'].lexicon.words())

    def test_indexation_disabled(self):
        fi = self.createFile('test.pdf')
        gsettings = GlobalSettings(self.portal)
        # indexation is enabled by default, so disable it
        gsettings.enable_indexation = False
        notify(ObjectInitializedEvent(fi))
        # make sure conversion was successfull
        self.failUnless(self._isSuccessfullyConverted(fi))
        annotations = IAnnotations(fi)['collective.documentviewer']
        self.failUnless(annotations['catalog'] is None)

    def test_indexation_switch_mode(self):
        '''
          Test that switching the indexation from enabled to disabled
          and the other way round keep the state consistent.
        '''
        fi = self.createFile('test.pdf')
        # indexation is enabled by default
        notify(ObjectInitializedEvent(fi))
        # make sure conversion was successfull
        self.failUnless(self._isSuccessfullyConverted(fi))
        annotations = IAnnotations(fi)['collective.documentviewer']
        # something is catalogued
        self.failUnless(annotations['catalog'] is not None)
        # now disable indexation and convert again
        gsettings = GlobalSettings(self.portal)
        gsettings.enable_indexation = False
        # make it convertable again by adapting last_updated and filehash
        annotations['last_updated'] = DateTime('1901/01/01').ISO8601()
        annotations['filehash'] = 'dummymd5'
        notify(ObjectInitializedEvent(fi))
        # make sure conversion was successfull
        self.failUnless(self._isSuccessfullyConverted(fi))
        # nothing indexed anymore
        self.failIf(annotations['catalog'] is not None)

    def test_indexation_settings(self):
        '''
          The enable_indexation setting can be defined on the object
          local settings or in the global settings.  Local settings are
          overriding global settings...
        '''
        fi = self.createFile('test.pdf')
        # indexation is enabled by default in the global settings
        # and nothing is defined in the local settings
        notify(ObjectInitializedEvent(fi))
        # make sure conversion was successfull
        self.failUnless(self._isSuccessfullyConverted(fi))
        annotations = IAnnotations(fi)['collective.documentviewer']
        self.failUnless(annotations['catalog'] is not None)
        # nothing defined on the 'fi'
        self.failIf('enable_indexation' in annotations)
        # if we disable indexation in the local settings, this will be
        # taken into account as it overrides global settings
        annotations['enable_indexation'] = False
        # make it convertable again by adapting last_updated and filehash
        annotations['last_updated'] = DateTime('1901/01/01').ISO8601()
        annotations['filehash'] = 'dummymd5'
        notify(ObjectInitializedEvent(fi))
        # make sure conversion was successfull
        self.failUnless(self._isSuccessfullyConverted(fi))
        # as indexation is disabled in local settings, the text
        # of the PDF is no more indexed...
        self.failIf(annotations['catalog'] is not None)

    def _isSuccessfullyConverted(self, fi):
        '''
          Check if the given p_fi was successfully converted
        '''
        # make sure conversion was successfull
        settings = Settings(fi)
        return settings.successfully_converted


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)
