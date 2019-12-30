from persistent.dict import PersistentDict
from DateTime import DateTime
from zope.interface import implementer
from zope.annotation.interfaces import IAnnotations
from collective.documentviewer.interfaces import IDocumentViewerSettings
from collective.documentviewer.interfaces import IGlobalDocumentViewerSettings
from celery.result import AsyncResult


STORAGE_VERSION = 2

_defaults = {
    'storage_version': 1
}


class Base(object):
    use_interface = None

    def __init__(self, context):
        self.context = context
        annotations = IAnnotations(self.context)
        
        self._metadata = annotations.get('collective.documentviewer', None)
        if self._metadata is None:
            self._metadata = PersistentDict()
            self._metadata['last_updated'] = DateTime('1901/01/01').ISO8601()
            self.storage_version = STORAGE_VERSION
            annotations['collective.documentviewer'] = self._metadata
        '''if self._metadata.get('converting') == True:
            result = AsyncResult(self._metadata.get('celery_task_id'))
            if result:
                self._metadata['successfully_converted'] = True
                self._metadata['converting'] = False
                annotations['collective.documentviewer'] = self._metadata
           ''' 
    def __setattr__(self, name, value):
        if name[0] == '_' or name in ['context', 'use_interface']:
            self.__dict__[name] = value
        else:
            self._metadata[name] = value

    def __getattr__(self, name):
        default = None
        if name in self.use_interface.names():
            default = self.use_interface[name].default
        elif name in _defaults:
            default = _defaults.get(name, None)

        return self._metadata.get(name, default)

@implementer(IDocumentViewerSettings)
class Settings(Base):
    use_interface = IDocumentViewerSettings


@implementer(IGlobalDocumentViewerSettings)
class GlobalSettings(Base):
    use_interface = IGlobalDocumentViewerSettings
