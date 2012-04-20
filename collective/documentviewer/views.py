from zope.component import getUtility
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
from collective.documentviewer.async import isConversion, \
    asyncInstalled, QUOTA_NAME, queueJob
import shutil
from zope.annotation.interfaces import IAnnotations


from logging import getLogger
logger = getLogger('collective.documentviewer')

try:
    from plone.app.async.interfaces import IAsyncService
except ImportError:
    pass


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
        self.dvstatic = "%s/++resource++dv.resources" % (
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
            elif self.settings.successfully_converted is not None and \
                    not self.settings.successfully_converted:
                msg = "There was an error trying to convert the PDF. Maybe " +\
                      "the PDF is encrypted, corrupt or malformed? " +\
                      "Check log for details."
                self.enabled = False
            elif self.settings.successfully_converted is None:
                # must have just switched to this view
                msg = "This PDF is not yet converted to document viewer. " +\
                      "Please click the `Document Viewer Convert` button " +\
                      "to convert."
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
        width = either(self.settings.width,
                       self.global_settings.width)
        if width is None:
            width = "jQuery('#DV-container').width()"
        else:
            width = str(width)
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
if(hash.indexOf('#document') != -1 || (%(fullscreen)s &&
   hash != '#bypass-fullscreen')){
window.currentDocument = DV.load(window.documentData, {
    sidebar: true,
    search: %(search)s,
    container: document.body });
$('body').addClass('fullscreen');
}else{
window.currentDocument = DV.load(window.documentData, { %(height)s
    sidebar: %(sidebar)s,
    width: %(width)s,
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
    'width': width,
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
                self.context.getLayout() in ('documentviewer', 'page-turner')
        except:
            return False

    def async_enabled(self):
        return asyncInstalled()

    def cleanup_file_storage(self):
        """
        Cases to remove file storage.

        1) object not found
        2) found but not document viewer layout
        3) found, document viewer layout but blob storage set
        """
        gsettings = GlobalSettings(self.context)
        storage_loc = gsettings.storage_location
        if not os.path.exists(storage_loc):
            return 'storage location path "%s" does not exist' % storage_loc
        catalog = getToolByName(self.context, 'portal_catalog')
        for foldername in os.listdir(storage_loc):
            #foldername should be file uid
            brains = catalog(UID=foldername)
            folderpath = os.path.join(storage_loc, foldername)
            if len(brains) == 0:
                shutil.rmtree(folderpath)
            else:
                obj = brains[0].getObject()
                settings = Settings(obj)
                if obj.getLayout() != 'documentviewer':
                    if not settings.converting:
                        shutil.rmtree(folderpath)
                        # also delete settings
                        annotations = IAnnotations(obj)
                        data = annotations.get('collective.documentviewer',
                                               None)
                        if data:
                            del annotations['collective.documentviewer']
                elif settings.storage_type == 'Blob':
                    shutil.rmtree(folderpath)
        return 'done'


class Convert(Utils):

    def __call__(self):
        if self.enabled():
            settings = Settings(self.context)
            settings.last_updated = DateTime('1999/01/01').ISO8601()
            queueJob(self.context)
            if asyncInstalled():
                return super(Convert, self).__call__()

        self.request.response.redirect(self.context.absolute_url() + '/view')


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


class GroupView(BrowserView):

    def getContents(self, object=None, portal_type=('File',),
                    full_objects=False, path=None):
        if not object:
            object = self.context
        opts = {'portal_type': portal_type}
        if path:
            opts['path'] = path
        if 'q' in self.request.form and self.search_enabled:
            opts['SearchableText'] = self.request.form['q']
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
        self.search_enabled = self.global_settings.show_search_on_group_view

        self.portal_url = getMultiAdapter((self.context, self.request),
            name="plone_portal_state").portal_url()
        self.static_url = '%s/++resource++dv.resources' % (
            self.portal_url)
        self.resource_url = self.global_settings.override_base_resource_url
        self.dump_path = convert.DUMP_FILENAME.rsplit('.', 1)[0]
        return super(GroupView, self).__call__()

    def get_thumb(self, obj):
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
                return '%s/small/%s_1.%s' % (
                        dvpdffiles, self.dump_path, image_format)
            else:
                return '%s/images/pdf.png' % (self.static_url)
        elif obj.portal_type == 'Image':
            url = obj.absolute_url()
            return '%s/image_thumb' % url


class AsyncMonitor(BrowserView):
    """
    Monitor document conversions async jobs
    """

    def time_since(self, dt):
        now = DateTime('UTC')
        diff = now - dt

        secs = int(diff * 24 * 60 * 60)
        minutes = secs / 60
        hours = minutes / 60
        days = hours / 24

        if days:
            return '%i day%s' % (days, days > 1 and 's' or '')
        elif hours:
            return '%i hour%s' % (hours, hours > 1 and 's' or '')
        elif minutes:
            return '%i minute%s' % (minutes, minutes > 1 and 's' or '')
        else:
            return '%i second%s' % (secs, secs > 1 and 's' or '')

    def get_job_data(self, job, sitepath, removable=True):
        lastused = DateTime(job._p_mtime)
        if job.status != 'pending-status':
            timerunning = self.time_since(lastused)
        else:
            timerunning = '-'
        return {
            'status': job.status,
            'user': job.args[3],
            'object_path': '/'.join(job.args[0][len(sitepath):]),
            'lastused': lastused.toZone('UTC').pCommon(),
            'timerunning': timerunning,
            'removable': removable
        }

    @property
    def jobs(self):
        results = []
        if asyncInstalled():
            sitepath = self.context.getPhysicalPath()
            async = getUtility(IAsyncService)
            queue = async.getQueues()['']
            quota = queue.quotas[QUOTA_NAME]

            for job in quota._data:
                if isConversion(job, sitepath):
                    results.append(self.get_job_data(job, sitepath, False))

            jobs = [job for job in queue]
            for job in jobs:
                if isConversion(job, sitepath):
                    results.append(self.get_job_data(job, sitepath))
        return results

    def redirect(self):
        return self.request.response.redirect("%s/@@dvasync-monitor" % (
            self.context.absolute_url()))

    def remove(self):
        if self.request.get('REQUEST_METHOD', 'POST') and \
                self.request.form.get('form.action.remove', '') == 'Remove':
            # find the job
            sitepath = self.context.getPhysicalPath()
            async = getUtility(IAsyncService)
            queue = async.getQueues()['']

            objpath = self.request.form.get('path')
            object = self.context.restrictedTraverse(str(objpath), None)
            if object is None:
                return self.redirect()
            objpath = object.getPhysicalPath()

            jobs = [job for job in queue]
            for job in jobs:
                if isConversion(job, sitepath) and \
                        job.args[0] == objpath:
                    try:
                        queue.remove(job)
                        settings = Settings(object)
                        settings.converting = False
                    except LookupError:
                        pass
                    return self.redirect()
        return self.redirect()
