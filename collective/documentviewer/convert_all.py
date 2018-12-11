from collective.documentviewer.async import celeryInstalled
from collective.documentviewer.async import queueJob
from collective.documentviewer.settings import GlobalSettings
from collective.documentviewer.settings import Settings
from collective.documentviewer.utils import allowedDocumentType
from logging import getLogger
from Products.CMFCore.utils import getToolByName
from zope.component.hooks import getSite
from zope.globalrequest import getRequest

import transaction


logger = getLogger('collective.documentviewer')


def convert_all(only_unconverted=True):
    """Convert all files.
    Defaults to convert only files, which haven't been converted yet.
    """
    site = getSite()

    qi = getToolByName(site, 'portal_quickinstaller', None)
    if not qi:
        return
    if not qi.isProductInstalled('collective.documentviewer'):
        return
    if getRequest().get('plone.app.contenttypes_migration_running', False):
        """Don't migrate while running a plone.app.contenttypes migration.
        """
        return

    cat = getToolByName(site, 'portal_catalog')
    res = cat(portal_type='File')
    length = len(res)

    async_enabled = celeryInstalled()

    for cnt, item in enumerate(res, 1):

        logger.info('processing %s/%s', cnt, length)

        obj = item.getObject()

        settings = Settings(obj)
        if only_unconverted and settings.successfully_converted:
            continue

        gsettings = GlobalSettings(site)

        if not allowedDocumentType(obj, gsettings.auto_layout_file_types):
            continue

        auto_layout = gsettings.auto_select_layout
        if auto_layout and obj.getLayout() != 'documentviewer':
            obj.setLayout('documentviewer')

        if obj.getLayout() == 'documentviewer' and gsettings.auto_convert:
            queueJob(obj)
            if not async_enabled:
                # conversion lasts an eternity. commit the results immediately.
                transaction.commit()
