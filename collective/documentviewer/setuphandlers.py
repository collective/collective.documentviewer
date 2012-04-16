from Products.CMFCore.utils import getToolByName
from Products.ATContentTypes.interface.file import IFileContent
from zope.annotation.interfaces import IAnnotations
import shutil
from settings import GlobalSettings
from zope.app.component.hooks import getSite
import os


def uninstall(context):

    if not context.readDataFile('collective.documentviewer-uninstall.txt'):
        return

    portal = context.getSite()
    portal_actions = getToolByName(portal, 'portal_actions')
    object_buttons = portal_actions.object

    actions_to_remove = ('documentviewer_settings', 'documentviewer_convert')
    for action in actions_to_remove:
        if action in object_buttons.objectIds():
            object_buttons.manage_delObjects([action])

    catalog = getToolByName(portal, 'portal_catalog')
    objs = catalog(object_provides=IFileContent.__identifier__)
    settings = GlobalSettings(getSite())

    for obj in objs:
        obj = obj.getObject()
        obj.layout = ''
        annotations = IAnnotations(obj)
        data = annotations.get('collective.documentviewer', None)
        if data:
            del annotations['collective.documentviewer']
        # delete files associated with it...
        storage_dir = os.path.join(settings.storage_location, context.UID())
        if os.path.exists(storage_dir):
            shutil.rmtree(storage_dir)
    types = getToolByName(portal, 'portal_types')
    filetype = types['File']
    methods = list(filetype.view_methods)
    methods = methods.remove('documentviewer')
    filetype.view_methods = tuple(methods)
