from logging import getLogger
from zope.app.component.hooks import getSite
from Products.CMFCore.utils import getToolByName
from collective.documentviewer.settings import GlobalSettings
from collective.documentviewer.utils import allowedDocumentType
from collective.documentviewer.async import queueJob

logger = getLogger('collective.documentviewer')


def handle_file_creation(object, event):
    qi = getToolByName(object, 'portal_quickinstaller')
    if not qi.isProductInstalled('collective.documentviewer'):
        return

    site = getSite()
    gsettings = GlobalSettings(site)

    if not allowedDocumentType(object, gsettings.auto_layout_file_types):
        return

    auto_layout = gsettings.auto_select_layout
    if auto_layout and object.getLayout() != 'documentviewer':
        object.setLayout('documentviewer')

    if object.getLayout() == 'documentviewer' and gsettings.auto_convert:
        queueJob(object)
