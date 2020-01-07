from logging import getLogger

from collective.documentviewer.convert import Converter, runConversion
from collective.documentviewer.settings import Settings
from ZODB.POSException import ConflictError
from zope.component.hooks import getSite

logger = getLogger('collective.documentviewer')


try:
    from celery.result import AsyncResult  # noqa
except ImportError:
    pass


def celeryInstalled():
    try:
        import collective.celery  # noqa
        return True
    except Exception:
        return False


def isConversion(job, sitepath):
    """
    Check if job is a document viewer conversion job
    """
    return sitepath == job.args[1] and job.args[4] == runConversion


def getJobRunner(obj):
    if celeryInstalled():
        return CeleryJobRunner(obj)


try:
    from collective.celery import task

    @task()
    def _celeryQueueJob(obj):
        retries = 0
        while True:
            try:
                return runConversion(obj)
            except ConflictError:
                retries += 1
                if retries > 4:
                    break
except ImportError:
    pass


class CeleryJobRunner(object):
    """
    helper class to setup the quota and check the
    queue before adding it to the queue
    """

    def __init__(self, obj):
        self.object = obj
        self.portal = getSite()
        self.settings = Settings(obj)

    def is_current_active(self, job):
        try:
            return job.state not in ('PENDING', 'FAILURE', 'SUCCESS', 'RETRY')
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
        if not self.settings.celery_task_id:
            return -1, None

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


def celeryQueueJob(obj):
    try:
        runner = CeleryJobRunner(obj)
        if runner.already_in_queue:
            logger.info('object %s already in queue for conversion' % (
                repr(obj)))
        else:
            runner.queue_it()
        return
    except Exception:
        raise QueueException


def queueJob(obj):
    converter = Converter(obj)
    if not converter.can_convert:
        return
    try:
        if celeryInstalled():
            celeryQueueJob(obj)
        else:
            converter(False)
    except QueueException:
        logger.exception(
            "Error using async with "
            "collective.documentviewer. Converting pdf without async...")
        converter()
