from zope.app.component.hooks import getSite
from Products.CMFCore.utils import getToolByName


def dvInstalled():
    qi = getToolByName(getSite(), 'portal_quickinstaller', None)
    if qi is None:
        return False
    return qi.isProductInstalled('collective.documentviewer')


def pt_queue_job(*args, **kwargs):
    if not dvInstalled():
        from wc.pageturner import events
        return events._old_queue_job(*args, **kwargs)
