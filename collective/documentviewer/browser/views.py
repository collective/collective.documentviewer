import json
from logging import getLogger
import os
import random
import shutil

from AccessControl import Unauthorized
from DateTime import DateTime
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import base_hasattr
from Products.Five.browser import BrowserView
from collective.documentviewer import mf as _
from collective.documentviewer import storage
from collective.documentviewer.async import getJobRunner
from collective.documentviewer.async import asyncInstalled
from collective.documentviewer.async import celeryInstalled
from collective.documentviewer.async import queueJob
from collective.documentviewer.convert import DUMP_FILENAME
from collective.documentviewer.convert import TEXT_REL_PATHNAME
from collective.documentviewer.convert import docsplit
from collective.documentviewer.interfaces import IFileWrapper
from collective.documentviewer.interfaces import IUtils
from collective.documentviewer.settings import GlobalSettings
from collective.documentviewer.settings import Settings
from collective.documentviewer.utils import allowedDocumentType
from collective.documentviewer.utils import getPortal
from persistent.dict import PersistentDict
from persistent.list import PersistentList
from repoze.catalog.query import Contains
from zope.annotation.interfaces import IAnnotations
from zope.component import getMultiAdapter
from zope.i18n import translate
from zope.interface import implements

logger = getLogger('collective.documentviewer')


def either(one, two):
    if one is None:
        return two
    return one


class DocumentViewerView(BrowserView):

    installed = docsplit is not None
    enabled = True

    def __call__(self):
        self.site = getPortal(self.context)
        self.settings = Settings(self.context)
        self.global_settings = GlobalSettings(self.site)

        self.portal_url = getMultiAdapter(
            (self.context, self.request),
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
        self.enabled = True

        if allowedDocumentType(self.context,
                               self.global_settings.auto_layout_file_types):
            if not self.installed:
                msg = _("Since you do not have docsplit installed on this "
                        "system, we can not render the pages of this document.")

            if self.settings.converting is not None and \
                    self.settings.converting:
                if self.settings.successfully_converted:
                    # there is a version that is already converted, show it.
                    self.enabled = True
                    msg = _("A new conversion to the Document Viewer "
                            "is currently being generated for this document."
                            )
                else:
                    msg = _("The document is currently being converted to the "
                            "Document Viewer view.")
                    self.enabled = False
            elif self.settings.successfully_converted is not None and \
                    not self.settings.successfully_converted:
                msg = _("There was an error trying to convert the document. "
                        "Maybe the document is encrypted, corrupt or "
                        "malformed? Check log for details.")
                self.enabled = False
            elif self.settings.successfully_converted is None:
                # must have just switched to this view
                msg = _("This document is not yet converted to document "
                        "viewer. Please click the `Document Viewer Convert` "
                        "button in the actions menu to convert.")
                self.enabled = False
        else:
            self.enabled = False
            msg = _("The file is not a supported document type. "
                    "Your type may be supported. Check out the document "
                    "viewer configuration settings.")
        mtool = getToolByName(self.context, 'portal_membership')
        self.can_modify = mtool.checkPermission('Modify portal content',
                                                self.context)
        if msg and self.can_modify:
            utils.addPortalMessage(_(msg))

        return self.index()

    def annotations(self):
        data = []
        annotations = self.settings.annotations
        if annotations is None:
            return data

        for page, anns in annotations.items():
            for ann in anns:
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

        mtool = getToolByName(self.context, 'portal_membership')
        contributor_user = mtool.getMemberById(contributor)
        if contributor_user is not None:
            contributor = contributor_user.getProperty('fullname', None) \
                or contributor

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

    def getTranslatedJSLabels(self):
        """
        """
        labels = [
            ('zoom', 'Zoom'),
            ('page', 'Page'),
            ('of', 'of'),
            ('document', 'Document'),
            ('pages', 'Pages'),
            ('notes', 'Notes'),
            ('loading', 'Loading'),
            ('text', 'Text'),
            ('search', 'Search'),
            ('for', 'for'),
            ('previous', 'Previous'),
            ('next', 'Next'),
            ('close', 'Close'),
            ('remove', 'Remove'),
            ('link_to_note', 'Link to this note'),
            ('previous_annotation', 'Previous annotation'),
            ('next_annotation', 'Next annotation'),
            ('on_page', 'on page'),
            ('for_page', 'for page'),
            ('original_document', 'Original Document'),
            ('contributed_by', 'Contributed by:'),
            ('close_fullscreen', 'Close Fullscreen')
        ]
        result = ''
        for lid, default in labels:
            translated = translate(
                'js_label_%s' % lid, domain='collective.documentviewer',
                context=self.request, default=default)
            result += "var dv_translated_label_%s = '%s';\n" % (
                lid, translated.replace("'", "\\'")
            )
        self.request.response.setHeader("Content-type", "application/javascript")

        return result


try:
    from plone.dexterity.browser.view import DefaultView

    class DXDocumentViewerView(DocumentViewerView, DefaultView):
        def __call__(self):
            self._update()
            self.update()
            return super(DXDocumentViewerView, self).__call__()
except ImportError:
    pass


class DocumentViewerSearchView(BrowserView):

    def __call__(self):
        settings = Settings(self.context)
        catalog = settings.catalog
        query = self.request.form.get('q')
        if catalog:
            results = catalog.query(Contains('text', query))
            return json.dumps({
                "results": list(results[1]),
                "query": query
                })

        return json.dumps({"results": [], "query": query})


class Utils(BrowserView):
    implements(IUtils)

    def enabled(self):
        try:
            fw = IFileWrapper(self.context)
            if fw.has_enclosure:
                if self.context.getLayout() == 'documentviewer':
                    return True
                else:
                    settings = GlobalSettings(getPortal(self.context))
                    return allowedDocumentType(
                        self.context, settings.auto_layout_file_types)
            else:
                return False
        except:
            return False

    def settings_enabled(self):
        return self.context.getLayout() == 'documentviewer'

    def async_enabled(self):
        return asyncInstalled() or celeryInstalled()

    def clean_folder(self, catalog, storage_loc):
        if not os.path.isdir(storage_loc):
            return 0
        count = 0
        for foldername in os.listdir(storage_loc):
            if len(foldername) == 1:
                # we're in a container, check inside
                count += self.clean_folder(
                    catalog, os.path.join(storage_loc, foldername))
            else:
                # foldername should be file uid
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
        self.async_installed = asyncInstalled() or celeryInstalled()
        self.converting = False
        if self.enabled():
            req = self.request
            if req.get('REQUEST_METHOD', 'POST') and \
               'form.action.queue' in req.form.keys():
                authenticator = getMultiAdapter((self.context, self.request),
                                                name=u"authenticator")
                if not authenticator.verify():
                    raise Unauthorized

                settings = Settings(self.context)
                settings.last_updated = DateTime('1999/01/01').ISO8601()
                settings.filehash = '--foobar--'
                queueJob(self.context)
                self.converting = True
                return self.request.response.redirect(
                    self.context.absolute_url() + '/view')
            else:
                if self.async_installed:
                    self.position = getJobRunner(self.context).find_position()
                    if self.position > -1:
                        self.converting = True

            return super(Convert, self).__call__()

        self.request.response.redirect(self.context.absolute_url() + '/view')


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
        types = ('Folder', 'Large Plone Folder') + portal_type
        return self.getContents(portal_type=types)

    def get_files(self, obj, portal_type=('File',)):
        # Handle brains or objects
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

        self.portal_url = getMultiAdapter(
            (self.context, self.request),
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


class MoveJob(BrowserView):

    def __call__(self):
        if self.request.get('REQUEST_METHOD', 'POST') and \
                self.request.form.get('form.action.move', False):
            authenticator = getMultiAdapter((self.context, self.request),
                                            name=u"authenticator")
            if not authenticator.verify():
                raise Unauthorized

            getJobRunner(self.context).move_to_front()

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
                ann_id = int(req.form['id'])
                found = False
                annotations = annotations[page]
                for ann in annotations:
                    if ann['id'] == ann_id:
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
