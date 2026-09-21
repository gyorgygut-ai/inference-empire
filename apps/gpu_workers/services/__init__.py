from apps.gpu_workers.services.storage import Storage
from apps.gpu_workers.services.storage.r2_storage import R2Storage
from apps.gpu_workers.services.storage.r2_storage_fake import FakeR2Storage

__all__ = ["FakeR2Storage", "R2Storage", "Storage"]
