from collective.documentviewer.settings import Settings
from zope.component import getUtility
from collective.documentviewer.convert import runConversion
from zope.app.component.hooks import getSite
from collective.documentviewer.settings import GlobalSettings
from logging import getLogger
from collective.documentviewer.convert import Converter
from zc.async.interfaces import COMPLETED

logger = getLogger('collective.documentviewer')

QUOTA_NAME = 'dv'

try:
    from plone.app.async.interfaces import IAsyncService
except ImportError:
    pass


def asyncInstalled():
    try:
        import plone.app.async
        return True
    except:
        return False


def isConversion(job, sitepath):
    """
    Check if job is a document viewer conversion job
    """
    return sitepath == job.args[1] and job.args[4] == runConversion


class JobRunner(object):
    """
    helper class to setup the quota and check the
    queue before adding it to the queue
    """

    def __init__(self, object):
        self.object = object
        self.objectpath = self.object.getPhysicalPath()
        self.site = getSite()
        self.sitepath = self.site.getPhysicalPath()
        self.async = getUtility(IAsyncService)
        self.queue = self.async.getQueues()['']

    def is_current_active(self, job):
        return isConversion(job, self.sitepath) and \
            job.args[0] == self.objectpath and \
            job.status != COMPLETED

    @property
    def already_in_queue(self):
        """
        Check if object in queue
        """
        for job in self.queue.quotas[QUOTA_NAME]._data:
            if self.is_current_active(job):
                return True

        jobs = [job for job in self.queue]
        for job in jobs:
            if self.is_current_active(job):
                return True
        return False

    def set_quota(self):
        """
        Set quota for document viewer jobs
        """
        settings = GlobalSettings(self.site)
        size = settings.async_quota_size
        if QUOTA_NAME in self.queue.quotas:
            if self.queue.quotas[QUOTA_NAME].size != size:
                self.queue.quotas[QUOTA_NAME].size = size
                logger.info("quota %r configured in queue %r", QUOTA_NAME,
                            self.queue.name)
        else:
            self.queue.quotas.create(QUOTA_NAME, size=size)
            logger.info("quota %r added to queue %r", QUOTA_NAME,
                        self.queue.name)

    def queue_it(self):
        self.async.queueJobInQueue(self.queue, (QUOTA_NAME,), runConversion,
                                   self.object)
        settings = Settings(self.object)
        settings.converting = True


def queueJob(object):
    """
    queue a job async if available.
    otherwise, just run normal
    """
    converter = Converter(object)
    if not converter.can_convert:
        return
    if asyncInstalled():
        try:
            runner = JobRunner(object)
            if runner.already_in_queue:
                logger.info('object %s already in queue for conversion' % (
                    repr(object)))
            else:
                runner.set_quota()
                runner.queue_it()
            return
        except:
            logger.exception("Error using plone.app.async with "
                "collective.documentviewer. Converting pdf without "
                "plone.app.async...")
            converter()
    else:
        converter()
