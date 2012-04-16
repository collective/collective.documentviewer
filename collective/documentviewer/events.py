from zope.app.component.hooks import getSite
from settings import GlobalSettings
from Products.CMFCore.utils import getToolByName
from convert import convert
from zope.component import getUtility
from settings import Settings
from logging import getLogger

logger = getLogger('collective.documentviewer')

try:
    from plone.app.async.interfaces import IAsyncService
    async_installed = True
except:
    async_installed = False


def queue_job(object):
    if async_installed:
        try:
            settings = Settings(object)
            async = getUtility(IAsyncService)
            async.queueJob(convert, object)
            settings.converting = True
        except:
            logger.exception("Error using plone.app.async with "
                "collective.documentviewer. Converting pdf without "
                "plone.app.async...")
            convert(object)
    else:
        convert(object)


def handle_file_creation(object, event):
    qi = getToolByName(object, 'portal_quickinstaller')
    if not qi.isProductInstalled('collective.documentviewer'):
        return

    if object.getContentType() not in ('application/pdf', 'application/x-pdf',
                                       'image/pdf'):
        return
    site = getSite()
    gsettings = GlobalSettings(site)
    auto_layout = gsettings.auto_select_layout
    if auto_layout and object.getLayout() != 'documentviewer':
        object.setLayout('documentviewer')

    queue_job(object)
