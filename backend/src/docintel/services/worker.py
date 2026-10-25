import logging
import threading

from docintel.repositories.locking import RuntimeLock
from docintel.services.documents import DocumentService


class LocalInferenceWorker:
    """One bounded native inference at a time; pending work lives in SQLite, not RAM."""

    def __init__(self, service: DocumentService):
        self.service = service
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.run, name="document-inference", daemon=True)
        self.lock = RuntimeLock(service.settings.runtime_dir / "worker.lock")

    def start(self):
        self.lock.acquire()
        try:
            self.service.recover_interrupted()
            self.thread.start()
        except BaseException:
            self.lock.release()
            raise

    def run(self):
        while not self.stop.is_set():
            try:
                if not self.service.process_next():
                    self.stop.wait(0.25)
            except Exception:
                # Do not put source text, native stderr or disk paths in application logs.
                logging.getLogger(__name__).error("INFERENCE_WORKER_CYCLE_FAILED")
                self.stop.wait(1)

    def close(self):
        self.stop.set()
        self.thread.join(timeout=self.service.settings.provider_timeout_seconds + 5)
        if not self.thread.is_alive():
            self.lock.release()
