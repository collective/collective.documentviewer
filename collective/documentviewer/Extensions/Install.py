import os
import shutil
try:
    from zope.app.component.hooks import getSite
except ImportError:
    from zope.component.hooks import getSite
from zope.annotation.interfaces import IAnnotations
from collective.documentviewer.settings import GlobalSettings
from Products.CMFCore.utils import getToolByName
from collective.documentviewer.config import GROUP_VIEW_DISPLAY_TYPES
from collective.documentviewer import storage
from collective.documentviewer.upgrades import OBJECT_PROVIDES


def install(context):
    # when you override this, you have to manually run GS
    setup = getToolByName(context, 'portal_setup')
    setup.runAllImportStepsFromProfile(
        'profile-collective.documentviewer:default')

    types = getToolByName(context, 'portal_types')

    for portal_type in GROUP_VIEW_DISPLAY_TYPES:
        if portal_type in types.objectIds():
            _type = types[portal_type]
            methods = list(_type.view_methods)
            methods.append('dvpdf-group-view')
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
        objs = catalog(object_provides=OBJECT_PROVIDES)
        settings = GlobalSettings(portal)

        # remove annotations and reset view
        for obj in objs:
            obj = obj.getObject()
            if obj.getLayout() == 'documentviewer':
                obj.layout = ''
            annotations = IAnnotations(obj)
            data = annotations.get('collective.documentviewer', None)
            if data:
                del annotations['collective.documentviewer']
            # delete files associated with it...
            storage_dir = storage.getResourceDirectory(gsettings=settings, obj=obj)
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
        for portal_type in GROUP_VIEW_DISPLAY_TYPES:
            if portal_type in types.objectIds():
                _type = types[portal_type]
                methods = list(_type.view_methods)
                if 'dvpdf-group-view' in methods:
                    methods.remove('dvpdf-group-view')
                    _type.view_methods = tuple(set(methods))

        # remove control panel
        pcp = getToolByName(context, 'portal_controlpanel')
        pcp.unregisterConfiglet('documentviewer')
        pcp.unregisterConfiglet('documentviewer-jobs')

        # remove global settings annotations
        annotations = IAnnotations(portal)
        data = annotations.get('collective.documentviewer', None)
        if data:
            del annotations['collective.documentviewer']
