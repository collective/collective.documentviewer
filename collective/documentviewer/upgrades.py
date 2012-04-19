from zope.app.component.hooks import getSite
from logging import getLogger
from Products.CMFCore.utils import getToolByName
from collective.documentviewer.config import GROUP_VIEW_DISPLAY_TYPES

default_profile = 'profile-collective.documentviewer:default'
logger = getLogger('collective.documentviewer')


def upgrade_to_1_1(context):
    context.runImportStepFromProfile(default_profile, 'controlpanel')


def upgrade_to_1_2(context):
    # run 1.1 upgrade again since we change the control panel again
    upgrade_to_1_1(context)

    types = getToolByName(context, 'portal_types')
    old_display = 'dvpdf-album-view'

    logger.info('fixing group view name')
    for portal_type in GROUP_VIEW_DISPLAY_TYPES:
        if portal_type in types.objectIds():
            _type = types[portal_type]
            methods = list(_type.view_methods)
            if old_display in methods:
                methods.remove(old_display)
            methods.append('dvpdf-group-view')
            _type.view_methods = tuple(set(methods))

    logger.info('looking for any existing containers with view to fix')
    catalog = getToolByName(context, 'portal_catalog')
    for brain in catalog(portal_type=GROUP_VIEW_DISPLAY_TYPES):
        obj = brain.getObject()
        if obj.getLayout() == old_display:
            obj.setLayout('dvpdf-group-view')

    # could be assigned to site root also
    site = getSite()
    if site.getLayout() == old_display:
        site.setLayout('dvpdf-group-view')
