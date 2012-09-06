import random
from persistent.list import PersistentList
from persistent.dict import PersistentDict
from AccessControl import Unauthorized
import os
import json
import shutil
from logging import getLogger
from zExceptions import NotFound
from OFS.SimpleItem import SimpleItem
from Products.Five.browser import BrowserView
from DateTime import DateTime
from AccessControl import getSecurityManager
from webdav.common import rfc1123_date
from zope.component import getMultiAdapter
from zope.interface import implements
from zope.component import getUtility
from Products.Five.browser.resource import DirectoryResource
from Products.Five.browser.resource import Directory
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.annotation.interfaces import IAnnotations
from Products.CMFCore import permissions
from Products.CMFCore.utils import getToolByName
from Products.ATContentTypes.interface.file import IFileContent
from Products.CMFPlone.utils import base_hasattr
from repoze.catalog.query import Contains
from plone.app.blob.download import handleRequestRange
from plone.app.blob.iterators import BlobStreamIterator
from plone.app.blob.utils import openBlob
from z3c.form import form
from z3c.form import field
from z3c.form import button
from plone.app.z3cform.layout import wrap_form
from collective.documentviewer.utils import allowedDocumentType
from collective.documentviewer.interfaces import IDocumentViewerSettings
from collective.documentviewer.interfaces import IUtils
from collective.documentviewer.interfaces import IGlobalDocumentViewerSettings
from collective.documentviewer.settings import Settings
from collective.documentviewer.settings import GlobalSettings
from collective.documentviewer import mf as _
from collective.documentviewer.convert import docsplit
from collective.documentviewer.convert import DUMP_FILENAME
from collective.documentviewer.convert import TEXT_REL_PATHNAME
from collective.documentviewer.async import isConversion
from collective.documentviewer.async import asyncInstalled
from collective.documentviewer.async import QUOTA_NAME
from collective.documentviewer.async import queueJob
from collective.documentviewer.async import JobRunner
from collective.documentviewer import storage
from collective.documentviewer.utils import getPortal
from collective.documentviewer.interfaces import IBlobFileWrapper
from plone.memoize.request import memoize_diy_request

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
        self.site = getPortal(self.context)
        self.settings = Settings(self.context)
        self.global_settings = GlobalSettings(self.site)

        self.portal_url = getMultiAdapter((self.context, self.request),
            name="plone_portal_state").portal_url()
        self.dvstatic = "%s/++resource++dv.resources" % (
            self.portal_url)
        resource_url = self.global_settings.override_base_resource_url
        rel_url = storage.getResourceRelURL(gsettings=self.global_settings,
                                            settings=self.settings)
        if resource_url:
            self.dvpdffiles = '%s/%s' % (resource_url.rstrip('/'), rel_url)
        else:
            self.dvpdffiles = '%s/%s' % (self.portal_url, rel_url)

        utils = getToolByName(self.context, 'plone_utils')
        msg = None

        if allowedDocumentType(self.context,
                self.global_settings.auto_layout_file_types):
            if not self.installed:
                msg = "Since you do not have docsplit installed on this " + \
                      "system, we can not render the pages of this document."
            elif self.settings.converting is not None and \
                    self.settings.converting:
                msg = "The document is currently being converted to the " + \
                      "Document Viewer view."
                self.enabled = False
            elif self.settings.successfully_converted is not None and \
                    not self.settings.successfully_converted:
                msg = "There was an error trying to convert the document. " +\
                      "Maybe the document is encrypted, corrupt or " +\
                      "malformed? Check log for details."
                self.enabled = False
            elif self.settings.successfully_converted is None:
                # must have just switched to this view
                msg = "This document is not yet converted to document " +\
                      "viewer. Please click the `Document Viewer Convert` " +\
                      "button to convert."
                self.enabled = False
        else:
            self.enabled = False
            msg = "The file is not a supported document type. " + \
                  "Your type may be supported. Check out the document " + \
                  "viewer configuration settings."
        mtool = getToolByName(self.context, 'portal_membership')
        self.can_modify = mtool.checkPermission('cmf.ModifyPortalContent',
                                                self.context)
        if msg and self.can_modify:
            utils.addPortalMessage(msg)

        return self.index()

    def annotations(self):
        data = []
        annotations = self.settings.annotations
        if annotations is None:
            return data
        for page, anns in annotations.items():
            for idx, ann in enumerate(anns):
                data.append({
                    "location": {"image": ann['coord']},
                    "title": ann['title'],
                    "id": ann['id'],
                    "page": page,
                    "access": "public",
                    "content": ann['content']})
        return data

    def sections(self):
        sections = self.settings.sections
        if sections is None:
            return []
        return sections

    def dv_data(self):
        dump_path = DUMP_FILENAME.rsplit('.', 1)[0]
        if self.global_settings.override_contributor:
            contributor = self.global_settings.override_contributor
        else:
            contributor = self.context.Creator()
        if self.global_settings.override_organization:
            organization = self.global_settings.override_organization
        else:
            organization = self.site.title
        image_format = self.settings.pdf_image_format
        if not image_format:
            # oops, this wasn't set like it should have been
            # on alpha release. We'll default back to global
            # setting.
            image_format = self.global_settings.pdf_image_format
        return {
            'access': 'public',
            'annotations': self.annotations(),
            'sections': list(self.sections()),
            'canonical_url': self.context.absolute_url() + '/view',
            'created_at': DateTime(self.context.CreationDate()).aCommonZ(),
            'data': {},
            'description': self.context.Description(),
            'id': self.context.UID(),
            'pages': self.settings.num_pages,
            'updated_at': DateTime(self.context.ModificationDate()).aCommonZ(),
            'title': self.context.Title(),
            'source': '',
            "contributor": contributor,
            "contributor_organization": organization,
            'resources': {
                'page': {
                    'image': '%s/{size}/%s_{page}.%s' % (
                        self.dvpdffiles, dump_path,
                        image_format),
                    'text': '%s/%s/%s_{page}.txt' % (
                        self.dvpdffiles, TEXT_REL_PATHNAME, dump_path)
                },
                'pdf': self.context.absolute_url(),
                'thumbnail': '%s/small/%s_1.%s' % (
                    self.dvpdffiles, dump_path,
                    image_format),
                'search': '%s/dv-search.json?q={query}' % (
                        self.context.absolute_url())
            }
        }

    def javascript(self):
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
        return """
window.documentData = %(data)s;
var hash = window.location.hash;
window.initializeDV = function(){
/* We do this so we can reload it later when managing annotations */
    window.currentDocument = DV.load(window.documentData, { %(height)s
        sidebar: %(sidebar)s,
        width: %(width)s,
        search: %(search)s,
        container: '#DV-container' });
}
if(hash.search("\#(document|pages|text)\/") != -1 || (%(fullscreen)s &&
        hash != '#bypass-fullscreen')){
    window.currentDocument = DV.load(window.documentData, {
        sidebar: true,
        search: %(search)s,
        container: document.body });
    jQuery('body').addClass('fullscreen');
}else{
    window.initializeDV();
    jQuery('body').addClass('not-fullscreen');
}
""" % {
    'portal_url': self.portal_url,
    'height': height,
    'fullscreen': str(fullscreen).lower(),
    'sidebar': str(sidebar).lower(),
    'search': str(search).lower(),
    'width': width,
    'data': json.dumps(self.dv_data())
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
            if IFileContent.providedBy(self.context):
                if self.context.getLayout() == 'documentviewer':
                    return True
                else:
                    return allowedDocumentType(self.context,
                        GlobalSettings(
                            getPortal(self.context)).auto_layout_file_types)
            else:
                return False
        except:
            return False

    def settings_enabled(self):
        return self.context.getLayout() == 'documentviewer'

    def async_enabled(self):
        return asyncInstalled()

    def clean_folder(self, catalog, storage_loc):
        if not os.path.isdir(storage_loc):
            return 0
        count = 0
        for foldername in os.listdir(storage_loc):
            if len(foldername) == 1:
                # we're in a container, check inside
                count += self.clean_folder(catalog,
                    os.path.join(storage_loc, foldername))
            else:
                #foldername should be file uid
                brains = catalog(UID=foldername)
                folderpath = os.path.join(storage_loc, foldername)
                if len(brains) == 0:
                    shutil.rmtree(folderpath)
                    count += 1
                else:
                    obj = brains[0].getObject()
                    settings = Settings(obj)
                    if obj.getLayout() != 'documentviewer':
                        if not settings.converting:
                            shutil.rmtree(folderpath)
                            count += 1
                            # also delete settings
                            annotations = IAnnotations(obj)
                            data = annotations.get('collective.documentviewer',
                                                   None)
                            if data:
                                del annotations['collective.documentviewer']
                    elif settings.storage_type == 'Blob':
                        shutil.rmtree(folderpath)
                        count += 1
        return count

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
        number = self.clean_folder(catalog, storage_loc)
        return 'cleaned %i' % number


class Convert(Utils):

    def __call__(self):
        """
        - handle queuing
        - csrf protection
        - async
            - queue position
        """
        mtool = getToolByName(self.context, 'portal_membership')
        self.manager = mtool.checkPermission('cmf.ManagePortal',
                                             self.context)
        self.async_installed = asyncInstalled()
        self.converting = False
        if self.enabled():
            req = self.request
            if req.get('REQUEST_METHOD', 'POST') and \
                req.form.get('form.action.queue', '') == 'Convert':
                authenticator = getMultiAdapter((self.context, self.request),
                                                name=u"authenticator")
                if not authenticator.verify():
                    raise Unauthorized
                settings = Settings(self.context)
                settings.last_updated = DateTime('1999/01/01').ISO8601()
                settings.filehash = '--foobar--'
                queueJob(self.context)
                self.converting = True
                if self.async_installed:
                    self.position = JobRunner(self.context).find_position()
                    queueJob(self.context)
                else:
                    return self.request.response.redirect(
                        self.context.absolute_url() + '/view')
            else:
                if self.async_installed:
                    self.position = JobRunner(self.context).find_position()
                    if self.position > -1:
                        self.converting = True
            return super(Convert, self).__call__()

        self.request.response.redirect(self.context.absolute_url() + '/view')


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
        range = handleRequestRange(self.context, length, self.request,
            self.request.response)
        return BlobStreamIterator(blob, **range)


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
                return BlobFileWrapper(self.context, self.settings,
                    filepath, self.request).__of__(self.context)
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
        if len(self.previous) == 2 and (self.previous[0] != name[0] or \
                self.previous[1] != name[1:2]):
            # make sure the first two were a sub-set of the uid
            raise NotFound
        uidcat = getToolByName(self.site, 'uid_catalog')
        brains = uidcat(UID=name)
        if len(brains) == 0:
            raise NotFound
        fileobj = brains[0].getObject()
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
            res = object.queryCatalog(self.request, batch=True, **opts)
        else:
            opts['sort_on'] = 'getObjPositionInParent'
            res = object.getFolderContents(contentFilter=opts,
                                           batch=True, b_size=self.b_size,
                                           full_objects=full_objects)
        return res

    def results(self, portal_type=('File',)):
        result = {}
        types = ('Folder', 'Large Plone Folder') + portal_type
        return self.getContents(portal_type=types)
        return result

    def get_files(self, obj, portal_type=('File',)):
        #Handle brains or objects
        if base_hasattr(obj, 'getPath'):
            path = obj.getPath()
        else:
            path = '/'.join(obj.getPhysicalPath())
        # Explicitly set path to remove default depth
        return self.getContents(object=obj, portal_type=portal_type, path=path)

    @property
    def b_size(self):
        if self.context.portal_type == 'Topic':
            if self.context.getLimitNumber():
                return self.context.getItemCount()
        return self.global_settings.group_view_batch_size

    def __call__(self):
        self.site = getPortal(self.context)
        self.global_settings = GlobalSettings(self.site)
        self.search_enabled = self.global_settings.show_search_on_group_view

        self.portal_url = getMultiAdapter((self.context, self.request),
            name="plone_portal_state").portal_url()
        self.static_url = '%s/++resource++dv.resources' % (self.portal_url)
        self.resource_url = self.global_settings.override_base_resource_url
        self.dump_path = DUMP_FILENAME.rsplit('.', 1)[0]
        return super(GroupView, self).__call__()

    def get_thumb(self, obj):
        if not obj:
            return None
        resource_rel = storage.getResourceRelURL(obj=obj)
        if self.resource_url:
            dvpdffiles = '%s/%s' % (self.resource_url.rstrip('/'),
                                    resource_rel)
        else:
            dvpdffiles = '%s/%s' % (self.portal_url, resource_rel)

        if obj.portal_type == 'File':
            settings = Settings(obj)
            if settings.successfully_converted:
                image_format = settings.pdf_image_format
                if not image_format:
                    image_format = self.global_settings.pdf_image_format
                return '%s/small/%s_1.%s' % (dvpdffiles, self.dump_path,
                                             image_format)
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

    def move(self):
        pass

    def remove(self):
        if self.request.get('REQUEST_METHOD', 'POST') and \
                self.request.form.get('form.action.remove', '') == 'Remove':
            authenticator = getMultiAdapter((self.context, self.request),
                                            name=u"authenticator")
            if not authenticator.verify():
                raise Unauthorized
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


class MoveJob(BrowserView):

    def __call__(self):
        if self.request.get('REQUEST_METHOD', 'POST') and \
                self.request.form.get('form.action.move', False):
            authenticator = getMultiAdapter((self.context, self.request),
                                            name=u"authenticator")
            if not authenticator.verify():
                raise Unauthorized
            JobRunner(self.context).move_to_front()
        return self.request.response.redirect(
            self.context.absolute_url() + '/@@convert-to-documentviewer')


class Annotate(BrowserView):

    def __call__(self):
        req = self.request
        settings = Settings(self.context)
        annotations = settings.annotations
        if annotations is None:
            annotations = PersistentDict()
            settings.annotations = annotations
        sections = settings.sections
        if sections is None:
            sections = PersistentList()
            settings.sections = sections
        action = req.form['action']
        if action == 'addannotation':
            page = int(req.form['page'])
            if page not in annotations:
                annotations[page] = PersistentList()
            pageann = annotations[page]
            data = {
                "id": random.randint(1, 9999999),
                "coord": req.form['coord'],
                "title": req.form.get('title', ''),
                "content": req.form.get('content', '')}
            pageann.append(data)
            return json.dumps(data)
        elif action == 'removeannotation':
            page = int(req.form['page'])
            if page in annotations:
                id = int(req.form['id'])
                found = False
                annotations = annotations[page]
                for ann in annotations:
                    if ann['id'] == id:
                        found = ann
                        break
                if found:
                    annotations.remove(found)
        elif action == 'addsection':
            data = {
                'page': req.form['page'],
                'title': req.form['title']
            }
            sections.append(data)
            return json.dumps(data)
        elif action == 'removesection':
            data = {
                'page': req.form['page'],
                'title': req.form['title']
            }
            if data in sections:
                sections.remove(data)
