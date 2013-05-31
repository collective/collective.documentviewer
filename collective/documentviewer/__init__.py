from zope.i18nmessageid import MessageFactory
mf = MessageFactory('collective.documentviewer')
import adapters

def initialize(context):
    """Initializer called when used as a Zope 2 product."""
