'''
This needs a redis db and a redis queue worker running
$ rq worker --with-scheduler
'''
from typing import Callable, Generic

from rq import Queue
from rq.job import Job
from redis import Redis

from climate_health.worker.interface import ReturnType
import logging
logger = logging.getLogger(__name__)

class RedisJob(Generic[ReturnType]):
    def __init__(self, job: Job):
        self._job = job

    @property
    def status(self) -> str:
        return self._job.get_status()

    @property
    def result(self) -> ReturnType | None:
        return self._job.return_value()

    @property
    def progress(self) -> float:
        return 0

    def cancel(self):
        self._job.cancel()

    @property
    def is_finished(self) -> bool:
        print(self._job.is_finished)
        if self._job.get_status() == 'queued':
            logger.warning('Job is queued, maybe no worker is set up? Run `$ rq worker`')
        print(self._job.get_status())

        return self._job.is_finished


class RedisQueue:
    def __init__(self):
        self.q = Queue(connection=Redis())

    def queue(self, func: Callable[..., ReturnType], *args, **kwargs) -> RedisJob[ReturnType]:
        return RedisJob(self.q.enqueue(func, *args, **kwargs))

    def __del__(self):
        self.q.connection.close()
