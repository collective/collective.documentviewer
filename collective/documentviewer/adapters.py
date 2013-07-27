import os

import zope.interface
from zope.cachedescriptors.property import Lazy as lazy_property
from zope.component import adapts
from zope.interface import implements, Interface

from OFS.interfaces import IItem
from Products.CMFCore.utils import getToolByName

from collective.documentviewer.interfaces import IFileWrapper, IOCRLanguage
from collective.documentviewer.iso639_2_utf8 import ISO_UTF_MAP

try:
    from Products.ATContentTypes.interface.file import IFileContent
except ImportError:
    class IFileContent(Interface):
        pass
try:
    from plone.dexterity.interfaces import IDexterityContent
except ImportError:
    class IDexterityContent(Interface):
        pass
try:
    from plone.rfc822.interfaces import IPrimaryFieldInfo
except ImportError:
    class IPrimaryFieldInfo(Interface):
        pass
try:
    from plone.namedfile.interfaces import INamedField
except ImportError:
    class INamedField(Interface):
        pass


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


class BaseItem(object):
    implements(IFileWrapper)
    adapts(IItem)

    def __init__(self, context):
        self.context = context

    @property
    def has_enclosure(self):
        return IFileContent.providedBy(self.context)

    @lazy_property
    def _field(self):
        return self.context.getField('file') or self.context.getPrimaryField()

    @lazy_property
    def file(self):
        if self.has_enclosure:
            wrapper = self._field.get(self.context)
            return wrapper

    @property
    def file_length(self):
        return self.file.get_size()

    @property
    def file_type(self):
        return self.context.getContentType()

    @property
    def blob(self):
        return self.file.getBlob()

    @property
    def filename(self):
        return self._field.getFilename(self.context)


class DexterityItem(BaseItem):
    adapts(IDexterityContent)

    def __init__(self, context):
        super(DexterityItem, self).__init__(context)
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
        return self.file.getSize()

    @property
    def file_type(self):
        if self.file:
            return self.file.contentType

    @property
    def blob(self):
        return self.file._blob

    @property
    def filename(self):
        return self.file.filename
