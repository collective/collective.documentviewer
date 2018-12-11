import os

import zope.interface
from collective.documentviewer.interfaces import IFileWrapper, IOCRLanguage
from collective.documentviewer.iso639_2_utf8 import ISO_UTF_MAP
from OFS.interfaces import IItem
from plone.dexterity.interfaces import IDexterityContent
from plone.namedfile.interfaces import INamedField
from plone.rfc822.interfaces import IPrimaryFieldInfo
from Products.CMFCore.utils import getToolByName
from zope.cachedescriptors.property import Lazy as lazy_property
from zope.component import adapts
from zope.interface import implements


class StandardOCRLanguageAdapter(object):
    """ Return the document language through a configurable
        adapter.
    """

    adapts(IItem)
    zope.interface.implements(IOCRLanguage)

    def __init__(self, context):
        self.context = context

    def getLanguage(self):
        """ Return OCR language as 3-char language code """

        # First sniff into $OCR_LANGUAGE environment variable
        lang = os.environ.get('OCR_LANGUAGE')
        if lang is not None:
            return lang

        # fallback to site language
        lt = getToolByName(self.context, 'portal_languages')
        lang = lt.getPreferredLanguage()
        return ISO_UTF_MAP.get(lang, 'eng')


class DexterityItem(object):
    implements(IFileWrapper)
    adapts(IDexterityContent)

    def __init__(self, context):
        self.context = context
        try:
            self.primary = IPrimaryFieldInfo(self.context, None)
        except TypeError:
            # plone/dexterity/primary.py raises TypeError("Could not adapt")
            # if there is not primary field
            self.primary = None

    @property
    def has_enclosure(self):
        if self.primary:
            return INamedField.providedBy(self.primary.field)
        else:
            return False

    @lazy_property
    def file(self):
        if self.has_enclosure:
            return self.primary.field.get(self.context)

    @property
    def file_length(self):
        if self.file:
            return self.file.getSize()

    @property
    def file_type(self):
        if self.file:
            return self.file.contentType

    @property
    def blob(self):
        if self.file:
            return self.file._blob

    @property
    def filename(self):
        if self.file:
            return self.file.filename
