from collective.documentviewer.utils import allowedDocumentType
import os
from zExceptions import NotFound
from Products.Five.browser import BrowserView
from zope.interface import implements
from Products.CMFCore.utils import getToolByName
from interfaces import IDocumentViewerSettings, IUtils, \
    IGlobalDocumentViewerSettings
from settings import Settings, GlobalSettings
from Products.ATContentTypes.interface.file import IFileContent
from collective.documentviewer import mf as _
from zope.component import getMultiAdapter
from convert import docsplit
from zope.app.component.hooks import getSite
from collective.documentviewer.events import queue_job
from DateTime import DateTime
import json
from zope.browserresource.directory import DirectoryResource, Directory
from zope.browserresource.metaconfigure import allowed_names
from zope.security.checker import CheckerPublic, NamesChecker
from OFS.SimpleItem import SimpleItem
from zope.publisher.interfaces.browser import IBrowserPublisher
from collective.documentviewer import convert
from repoze.catalog.query import Contains
from plone.app.blob.download import handleRequestRange
from plone.app.blob.iterators import BlobStreamIterator
from plone.app.blob.utils import openBlob
from webdav.common import rfc1123_date
from Products.CMFPlone.utils import base_hasattr
from z3c.form import form, field, button
from plone.app.z3cform.layout import wrap_form

from logging import getLogger
logger = getLogger('collective.documentviewer')


def either(one, two):
    if one is None:
        return two
    return one


class DocumentViewerView(BrowserView):

    installed = docsplit is not None
    enabled = docsplit is not None

    def __call__(self):
        self.site = getSite()
        self.settings = Settings(self.context)
        self.global_settings = GlobalSettings(self.site)

        self.portal_url = getMultiAdapter((self.context, self.request),
            name="plone_portal_state").portal_url()
        self.dvstatic = "%s/++resource++documentviewer.resources" % (
            self.portal_url)
        resource_url = self.global_settings.override_base_resource_url
        if resource_url:
            self.dvpdffiles = '%s/%s' % (resource_url.rstrip('/'),
                                         self.context.UID())
        else:
            self.dvpdffiles = '%s/@@dvpdffiles/%s' % (
                self.portal_url, self.context.UID())

        utils = getToolByName(self.context, 'plone_utils')
        msg = None

        if allowedDocumentType(self.context,
                self.global_settings.auto_layout_file_types):
            if not self.installed:
                msg = "Since you do not have docspilt installed on this " + \
                      "system, we can not render the pages of this PDF."
            elif self.settings.converting is not None and \
                    self.settings.converting:
                msg = "The PDF is currently being converted to the " + \
                      "Document Viewer view..."
                self.enabled = False
            elif not self.settings.successfully_converted:
                msg = "There was an error trying to convert the PDF. Maybe " +\
                      "the PDF is encrypted, corrupt or malformed?"
                self.enabled = False
        else:
            self.enabled = False
            msg = "The file is not a PDF. No need for this view."

        if msg:
            mtool = getToolByName(self.context, 'portal_membership')
            if mtool.checkPermission('cmf.ModifyPortalContent', self.context):
                utils.addPortalMessage(msg)

        return self.index()

    def javascript(self):
        dump_path = convert.DUMP_FILENAME.rsplit('.', 1)[0]
        if self.global_settings.override_contributor:
            contributor = self.global_settings.override_contributor
        else:
            contributor = self.context.Creator()
        if self.global_settings.override_organization:
            organization = self.global_settings.override_organization
        else:
            organization = self.site.title
        fullscreen = self.settings.fullscreen
        height = 'height: %i,' % either(self.settings.height,
                                       self.global_settings.height)
        sidebar = either(self.settings.show_sidebar,
                         self.global_settings.show_sidebar)
        search = either(self.settings.show_search,
                        self.global_settings.show_search)
        image_format = self.settings.pdf_image_format
        if not image_format:
            # oops, this wasn't set like it should have been
            # on alpha release. We'll default back to global
            # setting.
            image_format = self.global_settings.pdf_image_format

        return """
window.documentData = %(data)s;
var hash = window.location.hash;
if(hash == '#document/p1' || (%(fullscreen)s && hash != '#bypass-fullscreen')){
window.currentDocument = DV.load(window.documentData, {
    sidebar: true,
    width: $('#DV-container').width(),
    search: %(search)s,
    container: document.body });
$('body').addClass('fullscreen');
}else{
window.currentDocument = DV.load(window.documentData, { %(height)s
    sidebar: %(sidebar)s,
    width: $('#DV-container').width(),
    search: %(search)s,
    container: '#DV-container' });
$('body').addClass('not-fullscreen');
}
""" % {
    'portal_url': self.portal_url,
    'height': height,
    'fullscreen': str(fullscreen).lower(),
    'sidebar': str(sidebar).lower(),
    'search': str(search).lower(),
    'data': json.dumps({
        'access': 'public',
        'annotations': [],
        'canonical_url': self.context.absolute_url() + '/view',
        'created_at': DateTime(self.context.CreationDate()).aCommonZ(),
        'data': {},
        'description': self.context.Description(),
        'id': self.context.UID(),
        'pages': self.settings.num_pages,
        'updated_at': DateTime(self.context.ModificationDate()).aCommonZ(),
        'title': self.context.Title(),
        'source': '',
        'sections': [],
        "contributor": contributor,
        "contributor_organization": organization,
        'resources': {
            'page': {
                'image': '%s/{size}/%s_{page}.%s' % (
                    self.dvpdffiles, dump_path,
                    image_format),
                'text': '%s/%s/%s_{page}.txt' % (
                    self.dvpdffiles, convert.TEXT_REL_PATHNAME, dump_path)
            },
            'pdf': self.context.absolute_url(),
            'thumbnail': '%s/small/%s_1.%s' % (
                self.dvpdffiles, dump_path,
                image_format),
            'search': '%s/dv-search.json?q={query}' % (
                    self.context.absolute_url())
        }
    })
}


class DocumentViewerSearchView(BrowserView):

    def __call__(self):
        settings = Settings(self.context)
        catalog = settings.catalog
        if catalog:
            query = self.request.form.get('q')
            results = catalog.query(Contains('text', query))
            return json.dumps({
                "results": list(results[1]),
                "query": query
                })
        return json.dumps({"results": [], "query": query})


class SettingsForm(form.EditForm):
    """
    The page that holds all the slider settings
    """
    fields = field.Fields(IDocumentViewerSettings)

    label = _(u'heading_documentviewer_settings_form',
        default=u"Document Viewer Settings")
    description = _(u'description_documentviewer_settings_form',
        default=u"these settings override the global settings.")

    @button.buttonAndHandler(_('Save'), name='apply')
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        self.applyChanges(data)

        url = getMultiAdapter((self.context, self.request),
            name='absolute_url')() + '/view'
        self.request.response.redirect(url)
SettingsFormView = wrap_form(SettingsForm)


class GlobalSettingsForm(form.EditForm):
    fields = field.Fields(IGlobalDocumentViewerSettings)

    label = _(u'heading_documentviewer_global_settings_form',
        default=u"Global Document Viewer Settings")
    description = _(u'description_documentviewer_global_settings_form',
        default=u"Configure the parameters for this Viewer.")

    @button.buttonAndHandler(_('Save'), name='apply')
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        self.applyChanges(data)

        self.status = u'Changes saved...'
GlobalSettingsFormView = wrap_form(GlobalSettingsForm)


class Utils(BrowserView):
    implements(IUtils)

    def enabled(self):
        try:
            return IFileContent.providedBy(self.context) and \
                self.context.getLayout() == 'documentviewer'
        except:
            return False

    def convert(self):
        if self.enabled():
            settings = Settings(self.context)
            settings.last_updated = DateTime('1999/01/01').ISO8601()
            queue_job(self.context)

        self.request.response.redirect(self.context.absolute_url() + '/view')

    def convert_all(self):
        confirm = self.request.get('confirm', 'no')
        if confirm != 'yes':
            return 'You must append "?confirm=yes"'
        else:
            ptool = getToolByName(object, 'portal_properties')
            site_props = getattr(ptool, 'site_properties', None)
            auto_layout = site_props.getProperty(
                'documentviewer_auto_select_layout', False)

            catalog = getToolByName(self.context, 'portal_catalog')
            files = catalog(object_provides=IFileContent.__identifier__)
            for brain in files:
                file = brain.getObject()
                if file.getContentType() not in ('application/pdf',
                        'application/x-pdf', 'image/pdf'):
                    continue

                if auto_layout and file.getLayout() != 'documentviewer':
                    file.setLayout('documentviewer')

                self.request.response.write(
                    'Converting %s to documentviewer...\n' % (
                        file.absolute_url()))
                settings = Settings(file)
                settings.last_updated = DateTime('1999/01/01').ISO8601()
                queue_job(file)


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
                blob = self.settings.blob_files[filepath]
                blobfi = openBlob(blob)
                length = os.fstat(blobfi.fileno()).st_size
                blobfi.close()
                ext = os.path.splitext(os.path.normcase(name))[1][1:]
                if ext == 'txt':
                    ct = 'text/plain'
                else:
                    ct = 'image/%s' % ext
                self.request.response.setHeader('Last-Modified',
                    rfc1123_date(self.context._p_mtime))
                self.request.response.setHeader('Accept-Ranges', 'bytes')
                self.request.response.setHeader("Content-Length", length)
                self.request.response.setHeader('Content-Type', ct)
                range = handleRequestRange(self.context, length, self.request,
                    self.request.response)
                return BlobStreamIterator(blob, **range)
            else:
                raise NotFound
        else:
            fi = PDFTraverseBlobFile(self.context, self.settings,
                                     request, name)
            fi.__parent__ = self
            return fi.__of__(self)

    def browserDefault(self, request):
        '''See interface IBrowserPublisher'''
        return lambda: '', ()


class PDFFiles(SimpleItem, DirectoryResource):
    implements(IBrowserPublisher)

    def __init__(self, context, request):
        SimpleItem.__init__(self, context, request)

        self.__name__ = 'dvpdffiles'
        permission = CheckerPublic
        checker = NamesChecker(allowed_names + ('__getitem__', 'get'),
                           permission)
        self.site = getSite()
        self.global_settings = GlobalSettings(self.site)
        self.storage_type = self.global_settings.storage_type
        self.__dir = Directory(self.global_settings.storage_location,
            checker, self.__name__)

        DirectoryResource.__init__(self, self.__dir, request)
        self.__Security_checker__ = checker

    def publishTraverse(self, request, name):
        '''See interface IBrowserPublisher'''
        uidcat = getToolByName(self.site, 'uid_catalog')
        brains = uidcat(UID=name)
        if len(brains) == 0:
            return NotFound
        fileobj = brains[0].getObject()
        settings = Settings(fileobj)
        if settings.storage_type == 'Blob':
            fi = PDFTraverseBlobFile(fileobj, settings, request)
            fi.__parent__ = self
            return fi.__of__(self)
        else:
            return super(PDFFiles, self).publishTraverse(request, name)


class AlbumView(BrowserView):

    def getContents(self, object=None, portal_type=('File',),
                    full_objects=False, path=None):
        if not object:
            object = self.context
        opts = {'portal_type': portal_type}
        if path:
            opts['path'] = path
        if object.portal_type == 'Topic':
            res = object.queryCatalog(**opts)
        else:
            opts['sort_on'] = 'getObjPositionInParent'
            res = object.getFolderContents(contentFilter=opts,
                                           full_objects=full_objects)
        return res

    def results(self, portal_type=('File',)):
        result = {}
        result['files'] = self.getContents(portal_type=portal_type)
        result['folders'] = self.getContents(
            portal_type=('Folder', 'Large Plone Folder'))
        return result

    def get_files(self, obj, portal_type=('File',)):
        #Handle brains or objects
        if base_hasattr(obj, 'getPath'):
            path = obj.getPath()
        else:
            path = '/'.join(obj.getPhysicalPath())
        # Explicitly set path to remove default depth
        return self.getContents(object=obj, portal_type=portal_type, path=path)

    def __call__(self):
        self.site = getSite()
        self.global_settings = GlobalSettings(self.site)

        self.portal_url = getMultiAdapter((self.context, self.request),
            name="plone_portal_state").portal_url()
        self.resource_url = self.global_settings.override_base_resource_url
        self.dump_path = convert.DUMP_FILENAME.rsplit('.', 1)[0]
        return super(AlbumView, self).__call__()

    def get_scales(self, obj):
        if not obj:
            return None
        if self.resource_url:
            dvpdffiles = '%s/%s' % (self.resource_url.rstrip('/'),
                                         obj.UID())
        else:
            dvpdffiles = '%s/@@dvpdffiles/%s' % (
                self.portal_url, obj.UID())

        if obj.portal_type == 'File':
            settings = Settings(obj)
            if settings.successfully_converted:
                image_format = settings.pdf_image_format
                if not image_format:
                    image_format = self.global_settings.pdf_image_format
                return {
                    'small': '%s/small/%s_1.%s' % (
                        dvpdffiles, self.dump_path, image_format),
                    'large': '%s/normal/%s_1.%s' % (
                        dvpdffiles, self.dump_path, image_format),
                }
            else:
                # XXX need placeholders...
                return {'small': '', 'large': ''}
        elif obj.portal_type == 'Image':
            url = obj.absolute_url()
            return {
                'small': '%s/image_thumb' % url,
                'large': '%s/image_preview' % url
            }
