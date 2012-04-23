from os.path import join
from zope.app.component.hooks import getSite
from collective.documentviewer.settings import GlobalSettings
from collective.documentviewer.settings import Settings


def getResourceDirectory(gsettings=None, settings=None, obj=None):
    if gsettings is None:
        gsettings = GlobalSettings(getSite())
    if settings is None:
        settings = Settings(obj)
    uid = settings.context.UID()
    if settings.storage_version >= 2:
        return join(gsettings.storage_location, uid[0], uid[1], uid)
    else:
        return join(gsettings.storage_location, uid)


def getResourceRelURL(gsettings=None, settings=None, obj=None):
    if gsettings is None:
        gsettings = GlobalSettings(getSite())
    if settings is None:
        settings = Settings(obj)
    base = '@@dvpdffiles/'
    if gsettings.override_base_resource_url:
        base = ''
    uid = settings.context.UID()
    if settings.storage_version >= 2:
        return '%s%s/%s/%s' % (base, uid[0], uid[1], uid)
    else:
        return '%s%s' % (base, uid)
