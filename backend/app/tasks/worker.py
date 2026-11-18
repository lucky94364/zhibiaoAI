"""Serial durable worker; business handlers are added in their owning stages."""
import argparse
import logging
from threading import Event, Thread
from app.repositories.database import Database
from app.settings import Settings
from app.tasks.store import JobStore
from app.services.common import DomainError

logger = logging.getLogger(__name__)


def run_once(store, handlers=None):
    job = store.claim()
    if job is None:
        return False
    token, job_id = job['claim_token'], job['id']
    stopped = Event()
    lease_lost = Event()

    def heartbeat():
        while not stopped.wait(5):
            try:
                store.progress(job_id, token)
            except Exception:
                lease_lost.set()
                logger.exception('任务心跳失败：%s', job_id)
                return

    thread = Thread(target=heartbeat, daemon=True)
    thread.start()
    try:
        handler = (handlers or {}).get(job['kind'])
        if handler is None:
            store.finish(job_id, token, error={'code': 'JOB_HANDLER_UNAVAILABLE', 'message': '该业务处理器尚未实现，未执行业务副作用'})
        else:
            def progress(value):
                if lease_lost.is_set():
                    raise DomainError('VERSION_CONFLICT', '任务领取权已失效')
                store.progress(job_id, token, value)
            output = handler(job, progress)
            if not lease_lost.is_set():
                store.finish(job_id, token, output=output)
    except KeyboardInterrupt:
        store.finish(job_id, token, interrupted=True, error={'code': 'WORKER_INTERRUPTED', 'message': 'worker 已停止'})
        raise
    except DomainError as error:
        if error.code != 'VERSION_CONFLICT':
            store.finish(job_id, token, error={'code': error.code, 'message': error.message})
    except Exception:
        logger.exception('任务执行失败：%s', job_id)
        store.finish(job_id, token, error={'code': 'JOB_FAILED', 'message': '任务执行失败，请查看服务端日志'})
    finally:
        stopped.set()
        thread.join()
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true', help='恢复过期任务后最多领取一个任务')
    parser.add_argument('--recover-only', action='store_true')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    database = Database(Settings().database_url)
    store = JobStore(database)
    try:
        logger.info('恢复过期任务：%s', store.recover())
        if args.recover_only:
            return
        while True:
            store.recover()
            worked = run_once(store)
            if args.once:
                return
            if not worked:
                Event().wait(1)
    except KeyboardInterrupt:
        pass
    finally:
        database.engine.dispose()

if __name__ == '__main__':
    main()
