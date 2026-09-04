class DirectAsyncRunner:
    def run_sync(self, worker, **inputs):
        return worker.generate(**inputs)

    def run_async(self, worker, **inputs):
        return worker.generate(**inputs)
