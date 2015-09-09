from logging import getLogger

from AccessControl import Unauthorized
from DateTime import DateTime
from Products.CMFPlone import PloneMessageFactory
from Products.Five.browser import BrowserView
from collective.documentviewer import mf as _
from collective.documentviewer.async import QUOTA_NAME
from collective.documentviewer.async import asyncInstalled
from collective.documentviewer.async import isConversion
from collective.documentviewer.interfaces import IGlobalDocumentViewerSettings
from collective.documentviewer.settings import Settings
from plone.app.z3cform.layout import wrap_form
from z3c.form import button
from z3c.form import field
from z3c.form import form
from zope.component import getMultiAdapter
from zope.component import getUtility


logger = getLogger('collective.documentviewer')

try:
    from plone.app.async.interfaces import IAsyncService
except ImportError:
    pass


class AsyncMonitor(BrowserView):
    """
    Monitor document conversions async jobs
    """

    def time_since(self, dt):
        now = DateTime('UTC')
        diff = now - dt

        secs = int(diff * 24 * 60 * 60)
        minutes = secs / 60
        hours = minutes / 60
        days = hours / 24

        if days:
            return '%i day%s' % (days, days > 1 and 's' or '')
        elif hours:
            return '%i hour%s' % (hours, hours > 1 and 's' or '')
        elif minutes:
            return '%i minute%s' % (minutes, minutes > 1 and 's' or '')
        else:
            return '%i second%s' % (secs, secs > 1 and 's' or '')

    def get_job_data(self, job, sitepath, removable=True):
        lastused = DateTime(job._p_mtime)
        if job.status != 'pending-status':
            timerunning = self.time_since(lastused)
        else:
            timerunning = '-'

        return {
            'status': job.status,
            'user': job.args[3],
            'object_path': '/'.join(job.args[0][len(sitepath):]),
            'lastused': lastused.toZone('UTC').pCommon(),
            'timerunning': timerunning,
            'removable': removable
        }

    @property
    def jobs(self):
        results = []
        if asyncInstalled():
            sitepath = self.context.getPhysicalPath()
            async = getUtility(IAsyncService)
            queue = async.getQueues()['']
            quota = queue.quotas[QUOTA_NAME]

            for job in quota._data:
                if isConversion(job, sitepath):
                    results.append(self.get_job_data(job, sitepath, False))

            jobs = [job for job in queue]
            for job in jobs:
                if isConversion(job, sitepath):
                    results.append(self.get_job_data(job, sitepath))

        return results

    def redirect(self):
        return self.request.response.redirect("%s/@@dvasync-monitor" % (
            self.context.absolute_url()))

    def move(self):
        pass

    def remove(self):
        if self.request.get('REQUEST_METHOD', 'POST') and \
                self.request.form.get('form.action.remove', '') == 'Remove':
            authenticator = getMultiAdapter((self.context, self.request),
                                            name=u"authenticator")
            if not authenticator.verify():
                raise Unauthorized

            # find the job
            sitepath = self.context.getPhysicalPath()
            async = getUtility(IAsyncService)
            queue = async.getQueues()['']

            objpath = self.request.form.get('path')
            obj = self.context.restrictedTraverse(str(objpath), None)
            if obj is None:
                return self.redirect()

            objpath = obj.getPhysicalPath()

            jobs = [job for job in queue]
            for job in jobs:
                if isConversion(job, sitepath) and \
                        job.args[0] == objpath:
                    try:
                        queue.remove(job)
                        settings = Settings(obj)
                        settings.converting = False
                    except LookupError:
                        pass

                    return self.redirect()

        return self.redirect()


class GlobalSettingsForm(form.EditForm):
    fields = field.Fields(IGlobalDocumentViewerSettings)

    label = _(u'heading_documentviewer_global_settings_form',
              default=u"Global Document Viewer Settings")
    description = _(u'description_documentviewer_global_settings_form',
                    default=u"Configure the parameters for this Viewer.")

    @button.buttonAndHandler(_('Save'), name='apply')
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        self.applyChanges(data)

        self.status = PloneMessageFactory('Changes saved.')

GlobalSettingsFormView = wrap_form(GlobalSettingsForm)
