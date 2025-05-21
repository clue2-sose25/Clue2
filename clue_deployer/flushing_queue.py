import os
from csv import DictWriter
from queue import Empty, Queue


class FlushingQueue(Queue):
    def __init__(self, filename: str, buffer_size=60, fields=[]) -> None:
        super().__init__(2 * buffer_size)
        self.buffer_size = buffer_size
        self.filename = filename
        self.fields = fields

    def put(self, item):
        if self.qsize() >= self.buffer_size:
            self.flush()
        super().put(item)

    def flush(self):
        if not os.path.isfile(self.filename):
            with open(self.filename, "w") as f:
                DictWriter(f, fieldnames=self.fields).writeheader()
        with open(self.filename, "a") as f:
            writer = DictWriter(f, fieldnames=self.fields)
            for _ in range(self.buffer_size):
                try:
                    writer.writerow(self.get(block=False, timeout=None).to_dict())
                except Empty:
                    break
