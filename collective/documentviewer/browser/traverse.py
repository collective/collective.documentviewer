from logging import getLogger
import os

from AccessControl import Unauthorized
from AccessControl import getSecurityManager
from OFS.SimpleItem import SimpleItem
from Products.CMFCore import permissions
from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
from Products.Five.browser.resource import Directory
from Products.Five.browser.resource import DirectoryResource
from collective.documentviewer.interfaces import IBlobFileWrapper
from collective.documentviewer.settings import GlobalSettings
from collective.documentviewer.settings import Settings
from collective.documentviewer.utils import getPortal
from plone.app.blob.download import handleRequestRange
from plone.app.blob.iterators import BlobStreamIterator
from plone.app.blob.utils import openBlob
from webdav.common import rfc1123_date
from zExceptions import NotFound
from zope.annotation.interfaces import IAnnotations
from zope.interface import implements
from zope.publisher.interfaces.browser import IBrowserPublisher

logger = getLogger('collective.documentviewer')


class BlobView(BrowserView):

    def __call__(self):
        sm = getSecurityManager()
        if not sm.checkPermission(permissions.View, self.context.context):
            raise Unauthorized

        settings = self.context.settings
        filepath = self.context.filepath
        blob = settings.blob_files[filepath]
        blobfi = openBlob(blob)
        length = os.fstat(blobfi.fileno()).st_size
        blobfi.close()
        ext = os.path.splitext(os.path.normcase(filepath))[1][1:]
        if ext == 'txt':
            ct = 'text/plain'
        else:
            ct = 'image/%s' % ext

        self.request.response.setHeader('Last-Modified',
                                        rfc1123_date(self.context._p_mtime))
        self.request.response.setHeader('Accept-Ranges', 'bytes')
        self.request.response.setHeader("Content-Length", length)
        self.request.response.setHeader('Content-Type', ct)
        request_range = handleRequestRange(
            self.context, length, self.request, self.request.response)
        return BlobStreamIterator(blob, **request_range)


class BlobFileWrapper(SimpleItem):
    implements(IBlobFileWrapper, IBrowserPublisher)

    def __init__(self, fileobj, settings, filepath, request):
        self.context = fileobj
        self.settings = settings
        self.filepath = filepath
        self.request = request

    def browserDefault(self, request):
        return self, ('@@view',)


class PDFTraverseBlobFile(SimpleItem):
    """
    For traversing blob data store
    """
    implements(IBrowserPublisher)

    def __init__(self, fileobj, settings, request, previous=None):
        self.context = fileobj
        self.settings = settings
        self.request = request
        self.previous = previous

    def publishTraverse(self, request, name):
        if name not in ('large', 'normal', 'small', 'text'):
            filepath = '%s/%s' % (self.previous, name)
            if filepath in self.settings.blob_files:
                return BlobFileWrapper(self.context,
                                       self.settings,
                                       filepath,
                                       self.request).__of__(self.context)
            else:
                raise NotFound
        else:
            if self.previous is not None:
                # shouldn't be traversing this deep
                raise NotFound

            fi = PDFTraverseBlobFile(self.context, self.settings,
                                     request, name)
            fi.__parent__ = self
            return fi.__of__(self)

    def browserDefault(self, request):
        '''See interface IBrowserPublisher'''
        return lambda: '', ()


_marker = object()


class RequestMemo(object):

    key = 'plone.memoize_request'

    def __call__(self, func):

        def memogetter(*args, **kwargs):
            request = args[0]

            annotations = IAnnotations(request)
            cache = annotations.get(self.key, _marker)

            if cache is _marker:
                cache = annotations[self.key] = dict()

            key = (func.__module__, func.__name__)
            value = cache.get(key, _marker)
            if value is _marker:
                value = cache[key] = func(*args, **kwargs)
            return value
        return memogetter


@RequestMemo()
def _getPortal(request, context):
    return getPortal(context)


class PDFFiles(SimpleItem, DirectoryResource):
    implements(IBrowserPublisher)

    def __init__(self, context, request, previous=[]):
        SimpleItem.__init__(self, context, request)
        self.previous = previous

        self.__name__ = 'dvpdffiles'
        self.site = _getPortal(request, context)
        self.global_settings = GlobalSettings(self.site)
        self.storage_type = self.global_settings.storage_type
        self.__dir = Directory(
            os.path.join(self.global_settings.storage_location, *previous),
            self.__name__)

        DirectoryResource.__init__(self, self.__dir, request)

    def publishTraverse(self, request, name):
        if len(self.previous) > 2:
            raise NotFound

        if len(name) == 1:
            if len(self.previous) == 0:
                previous = [name]
            else:
                previous = self.previous
                previous.append(name)

            self.context.path = os.path.join(self.context.path, name)
            files = PDFFiles(self.context, request, previous)
            files.__parent__ = self
            return files.__of__(self)

        if len(self.previous) == 2 and (self.previous[0] != name[0] or
           self.previous[1] != name[1:2]):
            # make sure the first two were a sub-set of the uid
            raise NotFound

        cat = getToolByName(self.site, 'portal_catalog')
        brains = cat.unrestrictedSearchResults(UID=name)
        if len(brains) == 0:
            raise NotFound

#        fileobj = brains[0].getObject()
#        getObject raise Unauthorized because we are Anonymous in the traverser
        fileobj = brains[0]._unrestrictedGetObject()
        settings = Settings(fileobj)
        if settings.storage_type == 'Blob':
            fi = PDFTraverseBlobFile(fileobj, settings, request)
            fi.__parent__ = self
            return fi.__of__(self)
        else:
            # so permission checks for file object are applied
            # to file resource
            self.__roles__ = tuple(fileobj.__roles__) + ()
            if settings.obfuscated_filepath:
                # check if this thing isn't published...
                self.context.path = os.path.join(self.context.path, name)
                name = settings.obfuscate_secret

            fi = super(PDFFiles, self).publishTraverse(request, name)
            return fi