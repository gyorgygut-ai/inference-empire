from workers.services.platform.beam_platform import RealBeamPlatform
from workers.services.platform.beam_platform_fake import FakeBeamPlatform
from workers.services.platform.flash_platform import RealFlashPlatform
from workers.services.platform.flash_platform_fake import FakeFlashPlatform
from workers.services.platform.modal_platform import RealModalPlatform
from workers.services.platform.modal_platform_fake import FakeModalPlatform


def flash_platform_factory(target):
    """Target-only factory. Fake deploy = no-op; real = CLI commands (Todo 5)."""
    if target == "fake":
        return FakeFlashPlatform()
    if target == "live":
        return RealFlashPlatform()
    raise ValueError(f"unknown target: {target!r}")


def beam_platform_factory(target):
    """Target-only factory. Fake deploy = no-op; real = CLI commands (Todo 5)."""
    if target == "fake":
        return FakeBeamPlatform()
    if target == "live":
        return RealBeamPlatform()
    raise ValueError(f"unknown target: {target!r}")


def modal_platform_factory(target):
    """Target-only factory. Fake deploy = no-op; real = CLI commands (Todo 5)."""
    if target == "fake":
        return FakeModalPlatform()
    if target == "live":
        return RealModalPlatform()
    raise ValueError(f"unknown target: {target!r}")
