from logging import getLogger
from zope.component import getUtility
from collective.documentviewer.utils import getPortal
from collective.documentviewer.settings import Settings
from collective.documentviewer.convert import runConversion
from collective.documentviewer.settings import GlobalSettings
from collective.documentviewer.convert import Converter
try:
    from zc.async.interfaces import COMPLETED
except:
    COMPLETED = None

logger = getLogger('collective.documentviewer')

QUOTA_NAME = 'dv'

try:
    from plone.app.async.interfaces import IAsyncService
except ImportError:
    pass

try:
    from celery.result import AsyncResult  # noqa
except ImportError:
    pass


def asyncInstalled():
    try:
        import plone.app.async  # noqa
        return True
    except:
        return False


def celeryInstalled():
    try:
        import collective.celery  # noqa
        return True
    except:
        return False


def isConversion(job, sitepath):
    """
    Check if job is a document viewer conversion job
    """
    return sitepath == job.args[1] and job.args[4] == runConversion


def getJobRunner(obj):
    if asyncInstalled():
        return AsyncJobRunner(obj)
    elif celeryInstalled():
        return CeleryJobRunner(obj)


class AsyncJobRunner(object):
    """
    helper class to setup the quota and check the
    queue before adding it to the queue
    """

    def __init__(self, obj):
        self.object = obj
        self.objectpath = self.object.getPhysicalPath()
        self.portal = getPortal(obj)
        self.portalpath = self.portal.getPhysicalPath()
        self.async = getUtility(IAsyncService)
        self.queue = self.async.getQueues()['']

    def is_current_active(self, job):
        return isConversion(job, self.portalpath) and \
            job.args[0] == self.objectpath and \
            job.status != COMPLETED

    @property
    def already_in_queue(self):
        """
        Check if object in queue
        """
        return self.find_job()[0] > -1

    def find_position(self):
        # active in queue
        try:
            return self.find_job()[0]
        except KeyError:
            return -1

    def find_job(self):
        # active in queue
        if QUOTA_NAME not in self.queue.quotas:
            return -1, None
        for job in self.queue.quotas[QUOTA_NAME]._data:
            if self.is_current_active(job):
                return 0, job

        jobs = [job for job in self.queue]
        for idx, job in enumerate(jobs):
            if self.is_current_active(job):
                return idx + 1, job
        return -1, None

    def set_quota(self):
        """
        Set quota for document viewer jobs
        """
        settings = GlobalSettings(self.portal)
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

    def move_to_front(self):
        """
        Queue data is stored in buckets of queues.
        Because of this, you need to go through each
        bucket and find where the actual job is,
        then move it to the first bucket, first item
        of queue.
        """
        position, job = self.find_job()
        if position <= 1:
            return
        found_bucket = None
        for bucket in self.queue._queue._data:
            if job in bucket._data:
                found_bucket = bucket
                break
        jobs = list(found_bucket._data)
        jobs.remove(job)
        found_bucket._data = tuple(jobs)

        bucket = self.queue._queue._data[0]
        jobs = list(bucket._data)
        jobs.insert(0, job)
        bucket._data = tuple(jobs)


try:
    from collective.celery import task

    @task()
    def _celeryQueueJob(obj):
        runConversion(obj)
        settings = Settings(obj)
        settings.converting = True
except ImportError:
    pass


class CeleryJobRunner(object):
    """
    helper class to setup the quota and check the
    queue before adding it to the queue
    """

    def __init__(self, obj):
        self.object = obj
        self.portal = getPortal(obj)
        self.settings = Settings(obj)

    def is_current_active(self, job):
        try:
            return job.state not in ('PENDING', 'FAILURE', 'SUCCESS')
        except TypeError:
            return False

    @property
    def already_in_queue(self):
        """
        Check if object in queue
        """
        return self.find_job()[0] > -1

    def find_position(self):
        # active in queue
        try:
            return self.find_job()[0]
        except KeyError:
            return -1

    def find_job(self):
        result = AsyncResult(self.settings.celery_task_id)
        if self.is_current_active(result):
            return 0, result

        return -1, None

    def queue_it(self):
        result = _celeryQueueJob.delay(self.object)
        self.settings.celery_task_id = result.id
        self.settings.converting = True

    def move_to_front(self):
        pass


class QueueException(Exception):
    pass


def asyncQueueJob(obj):
    try:
        runner = AsyncJobRunner(obj)
        runner.set_quota()
        if runner.already_in_queue:
            logger.info('object %s already in queue for conversion' % (
                repr(obj)))
        else:
            runner.queue_it()
        return
    except:
        raise QueueException


def celeryQueueJob(obj):
    try:
        runner = CeleryJobRunner(obj)
        if runner.already_in_queue:
            logger.info('object %s already in queue for conversion' % (
                repr(obj)))
        else:
            runner.queue_it()
        return
    except:
        raise QueueException


def queueJob(obj):
    converter = Converter(obj)
    if not converter.can_convert:
        return
    try:
        if asyncInstalled():
            asyncQueueJob(obj)
        elif celeryInstalled():
            celeryQueueJob(obj)
        else:
            converter()
    except QueueException:
        logger.exception(
            "Error using async with "
            "collective.documentviewer. Converting pdf without async...")
        converter()
