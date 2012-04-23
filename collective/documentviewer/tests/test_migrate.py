from zope.annotation.interfaces import IAnnotations
from zope.event import notify
from Products.Archetypes.event import ObjectInitializedEvent

import unittest2 as unittest

from collective.documentviewer.tests import BaseTest


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


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)
