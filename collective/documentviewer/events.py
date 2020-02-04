from zope.interface import implementer
from zope.component.interfaces import ObjectEvent
from collective.documentviewer.interfaces import IConversionFinishedEvent


@implementer(IConversionFinishedEvent)
class ConversionFinishedEvent(ObjectEvent):

    def __init__(self, obj, status):
        self.object = obj
        self.status = status
