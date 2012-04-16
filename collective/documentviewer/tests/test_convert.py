# -*- coding: utf-8 -*-

import unittest2 as unittest

from zope.component import getMultiAdapter
from zope.component import getUtility

from plone.app.testing import TEST_USER_ID
from plone.app.testing import logout
from plone.app.testing import setRoles
from plone.registry import Registry
from plone.registry.interfaces import IRegistry

from Products.CMFCore.utils import getToolByName

from collective.documentviewer.testing import DocumentViewer_INTEGRATION_TESTING


class RegistryTest(unittest.TestCase):

    layer = DocumentViewer_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.ILayer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        # set up settings registry
        self.registry = Registry()


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)
