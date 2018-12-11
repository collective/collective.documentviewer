from AccessControl import Unauthorized
from collective.documentviewer import mf as _
from collective.documentviewer import storage
from collective.documentviewer.async import celeryInstalled
from collective.documentviewer.async import getJobRunner
from collective.documentviewer.async import queueJob
from collective.documentviewer.convert_all import convert_all
from collective.documentviewer.convert import docsplit
from collective.documentviewer.convert import DUMP_FILENAME
from collective.documentviewer.convert import TEXT_REL_PATHNAME
from collective.documentviewer.interfaces import IFileWrapper
from collective.documentviewer.interfaces import IUtils
from collective.documentviewer.settings import GlobalSettings
from collective.documentviewer.settings import Settings
from collective.documentviewer.utils import allowedDocumentType
from collective.documentviewer.utils import getPortal
from DateTime import DateTime
from logging import getLogger
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.resources import add_resource_on_request
from Products.CMFPlone.utils import base_hasattr
from Products.Five.browser import BrowserView
from repoze.catalog.query import Contains
from zope.annotation.interfaces import IAnnotations
from zope.component import getMultiAdapter
from zope.index.text.parsetree import ParseError
from zope.interface import implements
from plone.dexterity.browser.view import DefaultView

import json
import os
import shutil


logger = getLogger('collective.documentviewer')


def either(one, two):
    if one is None:
        return two
    return one


class DocumentViewerView(DefaultView):

    installed = docsplit is not None
    enabled = True

    def __call__(self):
        self._update()

        add_resource_on_request(self.request, 'documentviewer')

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

    def dv_data(self):
        dump_path = DUMP_FILENAME.rsplit('.', 1)[0]

        if self.global_settings.show_contributor:
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
        else:
            contributor = organization = ''

        image_format = self.settings.pdf_image_format
        if not image_format:
            # oops, this wasn't set like it should have been
            # on alpha release. We'll default back to global
            # setting.
            image_format = self.global_settings.pdf_image_format

        return {
            'annotations': [],
            'sections': [],
            'access': 'public',
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

    def pattern_options(self):
        height = either(self.settings.height, self.global_settings.height)
        width = either(self.settings.width, self.global_settings.width)

        if width is None:
            width = '100%'
        else:
            width = str(width)

        sidebar = either(self.settings.show_sidebar,
                         self.global_settings.show_sidebar)
        search = either(self.settings.show_search,
                        self.global_settings.show_search)
        return json.dumps({
            'height': height,
            'sidebar': sidebar,
            'search': search,
            'width': width,
            'data': self.dv_data()
        })


class DVPdfUrl(BrowserView):
    def __call__(self):
        """ Redirects to the url for the rendered PDF.

            We need to redirect, because the PDF can be stored on FS, instead
            of ZODB.
        """
        site = getPortal(self.context)
        settings = Settings(self.context)
        global_settings = GlobalSettings(site)

        portal_url = getMultiAdapter(
            (self.context, self.request),
            name="plone_portal_state").portal_url()

        resource_url = global_settings.override_base_resource_url
        rel_url = storage.getResourceRelURL(gsettings=global_settings,
                                            settings=settings)
        if resource_url:
            dvpdffiles = '%s/%s' % (resource_url.rstrip('/'), rel_url)
        else:
            dvpdffiles = '%s/%s' % (portal_url, rel_url)

        url = '%s/pdf/dump.pdf' % dvpdffiles
        self.request.response.redirect(url)


class DocumentViewerSearchView(BrowserView):

    def __call__(self):
        settings = Settings(self.context)
        catalog = settings.catalog
        query = self.request.form.get('q')
        results = None
        if query:
            try:
                results = catalog.query(Contains('text', query))
            except (TypeError, ParseError):
                pass
        if catalog and results:
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
        except Exception:
            return False

    def settings_enabled(self):
        return self.context.getLayout() == 'documentviewer'

    def async_enabled(self):
        return celeryInstalled()

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
        self.async_installed = celeryInstalled()
        self.converting = False
        if self.enabled():
            req = self.request
            if (req.get('REQUEST_METHOD', 'POST') and
                    'form.action.queue' in req.form.keys()):
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


class ConvertAllUnconvertedView(BrowserView):
    def __call__(self):
        """Convert all unconverted files.
        """
        convert_all(only_unconverted=True)
        return "Finished"
