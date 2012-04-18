import os
import shutil
from zope.app.component.hooks import getSite
from zope.annotation.interfaces import IAnnotations
from collective.documentviewer.settings import GlobalSettings
from Products.ATContentTypes.interface.file import IFileContent
from Products.CMFCore.utils import getToolByName

types_to_add_ablum_view = [
    'Folder',
    'Large Plone Folder',
    'Plone Site',
    'Topic'
]


def install(context):
    # when you override this, you have to manually run GS
    setup = getToolByName(context, 'portal_setup')
    setup.runAllImportStepsFromProfile(
        'profile-collective.documentviewer:default')

    types = getToolByName(context, 'portal_types')

    for portal_type in types_to_add_ablum_view:
        if portal_type in types.objectIds():
            _type = types[portal_type]
            methods = list(_type.view_methods)
            methods.append('dvpdf-album-view')
            _type.view_methods = tuple(set(methods))


def uninstall(context, reinstall=False):
    if not reinstall:
        portal = getSite()
        portal_actions = getToolByName(portal, 'portal_actions')
        object_buttons = portal_actions.object

        # remove actions
        actions_to_remove = ('documentviewer_settings',
                             'documentviewer_convert')
        for action in actions_to_remove:
            if action in object_buttons.objectIds():
                object_buttons.manage_delObjects([action])

        catalog = getToolByName(portal, 'portal_catalog')
        objs = catalog(object_provides=IFileContent.__identifier__)
        settings = GlobalSettings(getSite())

        # remove annotations and reset view
        for obj in objs:
            obj = obj.getObject()
            obj.layout = ''
            annotations = IAnnotations(obj)
            data = annotations.get('collective.documentviewer', None)
            if data:
                del annotations['collective.documentviewer']
            # delete files associated with it...
            storage_dir = os.path.join(settings.storage_location,
                                       context.UID())
            if os.path.exists(storage_dir):
                shutil.rmtree(storage_dir)

        # remove view
        types = getToolByName(portal, 'portal_types')
        filetype = types['File']
        methods = list(filetype.view_methods)
        if 'documentviewer' in methods:
            methods.remove('documentviewer')
            filetype.view_methods = tuple(methods)

        # remove pdf album view
        for portal_type in types_to_add_ablum_view:
            if portal_type in types.objectIds():
                _type = types[portal_type]
                methods = list(_type.view_methods)
                if 'dvpdf-album-view' in methods:
                    methods.remove('dvpdf-album-view')
                    _type.view_methods = tuple(set(methods))

        # remove control panel
        pcp = getToolByName(context, 'portal_controlpanel')
        pcp.unregisterConfiglet('documentviewer')

        # remove global settings annotations
        annotations = IAnnotations(portal)
        data = annotations.get('collective.documentviewer', None)
        if data:
            del annotations['collective.documentviewer']
