from Products.Five.browser import BrowserView
from plone.app.form import base as ploneformbase
from zope.interface import implements
from zope.formlib import form
from Products.CMFCore.utils import getToolByName
from interfaces import IDocumentViewerSettings, IUtils, \
    IGlobalDocumentViewerSettings
from settings import Settings, GlobalSettings
from Products.ATContentTypes.interface.file import IFileContent
from collective.documentviewer import mf as _
import zope.event
import zope.lifecycleevent
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

from logging import getLogger
logger = getLogger('collective.documentviewer')


class DocumentViewerView(BrowserView):

    installed = docsplit is not None
    enabled = docsplit is not None

    def __call__(self):
        self.portal_url = getMultiAdapter((self.context, self.request),
            name="plone_portal_state").portal_url()
        self.dvstatic = "%s/++resource++documentviewer.resources" % (
            self.portal_url)
        self.dvpdffiles = '%s/@@dvpdffiles/%s' % (
            self.portal_url, self.context.UID())

        self.site = getSite()
        self.settings = Settings(self.context)
        self.global_settings = GlobalSettings(self.site)

        utils = getToolByName(self.context, 'plone_utils')
        msg = None

        if self.context.getContentType() in ('application/pdf',
                'application/x-pdf', 'image/pdf'):
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
        return """
window.currentDocument = DV.load(%(data)s, { width: 680,
   height: 450,
   sidebar: false,
   text: true,
container: '#DV-container' });
""" % {
    'portal_url': self.portal_url,
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
                    self.global_settings.pdf_image_format),
                'text': '%s/%s/%s_{page}.txt' % (
                    self.dvpdffiles, convert.TEXT_REL_PATHNAME, dump_path)
            },
            'pdf': self.context.absolute_url(),
            'thumbnail': '%s/small/%s_1.%s' % (
                self.dvpdffiles, dump_path,
                self.global_settings.pdf_image_format),
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


class SettingsForm(ploneformbase.EditForm):
    """
    The page that holds all the slider settings
    """
    form_fields = form.FormFields(IDocumentViewerSettings)

    label = _(u'heading_documentviewer_settings_form',
        default=u"Document Viewer Settings")
    description = _(u'description_documentviewer_settings_form',
        default=u"these settings override the global settings.")

    @form.action(_(u"label_save", default="Save"),
                 condition=form.haveInputWidgets,
                 name=u'save')
    def handle_save_action(self, action, data):
        if form.applyChanges(self.context, self.form_fields, data,
                                                     self.adapters):
            zope.event.notify(
                zope.lifecycleevent.ObjectModifiedEvent(self.context))
            zope.event.notify(ploneformbase.EditSavedEvent(self.context))
            self.status = "Changes saved"
        else:
            zope.event.notify(ploneformbase.EditCancelledEvent(self.context))
            self.status = "No changes"

        # convert right now if password provided
        if data.get('encryption_password', None):
            settings = Settings(self.context)
            settings.last_updated = DateTime('1999/01/01').ISO8601()
            queue_job(self.context)

        url = getMultiAdapter((self.context, self.request),
            name='absolute_url')() + '/view'
        self.request.response.redirect(url)


class GlobalSettingsForm(ploneformbase.EditForm):
    form_fields = form.FormFields(IGlobalDocumentViewerSettings)

    label = _(u'heading_documentviewer_global_settings_form',
        default=u"Global Document Viewer Settings")
    description = _(u'description_documentviewer_global_settings_form',
        default=u"Configure the parameters for this Viewer.")

    @form.action(_(u"label_save", default="Save"),
                 condition=form.haveInputWidgets,
                 name=u'save')
    def _handle_save_action(self, action, data):
        if form.applyChanges(self.context, self.form_fields, data,
                             self.adapters):
            zope.event.notify(ploneformbase.EditSavedEvent(self.context))
            self.status = "Changes saved"
        else:
            zope.event.notify(ploneformbase.EditCancelledEvent(self.context))
            self.status = "No changes"
        self.request.response.redirect(
            self.context.absolute_url() + '/@@global-documentviewer-settings')


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


class PDFFiles(SimpleItem, DirectoryResource):
    implements(IBrowserPublisher)

    def __init__(self, context, request):
        SimpleItem.__init__(self, context, request)

        self.__name__ = 'dvpdffiles'
        permission = CheckerPublic
        checker = NamesChecker(allowed_names + ('__getitem__', 'get'),
                           permission)
        self.__dir = Directory('/opt/dvpdffiles', checker, self.__name__)

        DirectoryResource.__init__(self, self.__dir, request)
        self.__Security_checker__ = checker
