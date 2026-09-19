from apps.gpu_workers.services.storage.r2_storage import R2Storage
from apps.gpu_workers.services.storage.r2_storage_fake import FakeR2Storage
from apps.gpu_workers.services.storage.storage import Storage

__all__ = ["FakeR2Storage", "R2Storage", "Storage"]
