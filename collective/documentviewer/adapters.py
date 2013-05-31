import os
import zope.interface
from zope.component import adapts
from Products.CMFCore.utils import getToolByName
from Products.ATContentTypes.interfaces.file import IATFile
from collective.documentviewer.interfaces import IOCRLanguage
from collective.documentviewer.iso639_2_utf8 import ISO_UTF_MAP

class StandardOCRLanguageAdapter(object):
    """ Return the document language through a configurable
        adapter.
    """

    adapts(IATFile)
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
