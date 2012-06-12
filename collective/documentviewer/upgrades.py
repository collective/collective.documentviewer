import os
from logging import getLogger
from os.path import exists
import shutil
import transaction
from DateTime import DateTime
from zope.app.component.hooks import getSite
from Products.CMFCore.utils import getToolByName
from Products.ATContentTypes.interface.file import IFileContent
from collective.documentviewer.config import GROUP_VIEW_DISPLAY_TYPES
from collective.documentviewer.settings import GlobalSettings
from collective.documentviewer.settings import Settings
from collective.documentviewer.settings import STORAGE_VERSION
from collective.documentviewer.utils import allowedDocumentType
from collective.documentviewer.async import queueJob
from collective.documentviewer import storage
from collective.documentviewer.utils import mkdir_p

default_profile = 'profile-collective.documentviewer:default'
logger = getLogger('collective.documentviewer')


def convert_all(context):
    catalog = getToolByName(context, 'portal_catalog')
    portal = getSite()
    gsettings = GlobalSettings(portal)
    for brain in catalog(object_provides=IFileContent.__identifier__):
        file = brain.getObject()

        if not allowedDocumentType(file,
                gsettings.auto_layout_file_types):
            continue

        # let's not switch to the document viewer view
        # until the document is converted. The conversion
        # process will check if the layout is set correctly.
        if file.getLayout() != 'documentviewer':
            settings = Settings(file)
            settings.last_updated = DateTime('1999/01/01').ISO8601()
            queueJob(file)
        else:
            settings = Settings(file)
            # also convert if there was an error.
            if settings.successfully_converted == False:
                settings.last_updated = DateTime('1999/01/01').ISO8601()
                settings.filehash = ''
                queueJob(file)


def migrate_old_storage(context):
    catalog = getToolByName(context, 'portal_catalog')
    portal = getSite()
    gsettings = GlobalSettings(portal)
    for brain in catalog(object_provides=IFileContent.__identifier__):
        file = brain.getObject()
        if file.getLayout() == 'documentviewer':
            settings = Settings(file)
            if settings.storage_version == 1:
                if settings.storage_type == 'File':
                    current_location = storage.getResourceDirectory(
                        gsettings=gsettings, settings=settings)
                    if not exists(current_location):
                        raise Exception(
                            "oops, can't find storage location %s" % (
                                current_location))
                    settings.storage_version = STORAGE_VERSION
                    new_location = storage.getResourceDirectory(
                        gsettings=gsettings, settings=settings)
                    # only make base
                    mkdir_p(os.path.sep.join(
                        new_location.split(os.path.sep)[:-1]))
                    shutil.move(current_location, new_location)
                    # need to commit these eagerly since a failed
                    # migration could leave some migrated wrong
                    transaction.commit()
                else:
                    settings.storage_version = STORAGE_VERSION


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


def upgrade_to_1_4(context):
    context.runImportStepFromProfile(default_profile, 'actions')
