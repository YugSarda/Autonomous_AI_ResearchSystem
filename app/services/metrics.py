import time
class Metrics:
    def __init__(self):
        self.start = time.time()
        self.tokens = 0
        self.retrieved = 0

    def log_retrieval(self, count):
        self.retrieved += count

    def log_tokens(self, count):
        self.tokens += count

    def finish(self):
        return {
            "latency": time.time() - self.start,
            "tokens": self.tokens,
            "retrieved_docs": self.retrieved
        }