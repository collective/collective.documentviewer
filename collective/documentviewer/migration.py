# -*- coding: utf-8 -*-
from plone.app.contenttypes.migration.migration import ICustomMigrator
from zope.annotation.interfaces import IAnnotations
from zope.component import adapter
from zope.interface import implementer
from zope.interface import Interface

import logging


logger = logging.getLogger(__name__)
ANNOTATION_KEY = 'collective.documentviewer'


@implementer(ICustomMigrator)
@adapter(Interface)
class PACDocumentViewerMigator(object):
    """Migrator for annotations while running a plone.app.contenttypes
    migration.
    """
    def __init__(self, context):
        self.context = context

    def migrate(self, old, new):
        source_annotations = IAnnotations(old)
        settings = source_annotations.get(ANNOTATION_KEY, None)
        if settings is not None:
            target_annotations = IAnnotations(new)
            if target_annotations.get(ANNOTATION_KEY, None) is not None:
                logger.error('DocumentViewer settings exist on %s' %
                             new.absolute_url())
                return
            target_annotations[ANNOTATION_KEY] = settings
            logger.info('DocumentViewer settings migrated for %s' %
                        new.absolute_url())
