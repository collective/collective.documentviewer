from zope.interface import implements
from zope.component.interfaces import ObjectEvent
from collective.documentviewer.interfaces import IConversionFinishedEvent


class ConversionFinishedEvent(ObjectEvent):
    implements(IConversionFinishedEvent)

    def __init__(self, obj, status):
        self.object = obj
        self.status = status
