from zope.app.component.hooks import getSite
from settings import GlobalSettings
from Products.CMFCore.utils import getToolByName
from convert import Converter, run_conversion
from zope.component import getUtility
from settings import Settings
from logging import getLogger
from collective.documentviewer.utils import allowedDocumentType

logger = getLogger('collective.documentviewer')

try:
    from plone.app.async.interfaces import IAsyncService
    async_installed = True
except:
    async_installed = False


def queue_job(object):
    converter = Converter(object)
    if not converter.can_convert:
        return
    if async_installed:
        try:
            settings = Settings(object)
            async = getUtility(IAsyncService)
            async.queueJob(run_conversion, object)
            settings.converting = True
            return
        except:
            logger.exception("Error using plone.app.async with "
                "collective.documentviewer. Converting pdf without "
                "plone.app.async...")
            converter()
    else:
        converter()


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

    if gsettings.auto_convert:
        queue_job(object)
