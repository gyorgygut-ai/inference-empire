"""E2E dev tests for h3 comfy workers.

Per TEST_CHECKLIST.md: "Test code deploys test worker before all; undeploys after all."
Deploys each worker via CLI, calls the endpoint, verifies contract + R2 artifact.
"""
import pytest

from helpers import (
    call_beam_fl2va,
    deploy_beam_fl2va,
    deploy_flash_comfy,
    undeploy_beam,
    undeploy_flash_comfy,
    verify_artifact_video,
    verify_contract,
)


# --- Flash Comfy ---

@pytest.fixture(scope="module")
def flash_comfy_deployed():
    deploy_flash_comfy()
    try:
        yield
    finally:
        undeploy_flash_comfy()


def test_e2e_dev_flash_comfy_returns_contract_and_uploads_artifact(flash_comfy_deployed):
    """generate() with good input -> returns output contract, R2 bucket has artifact."""
    data = {
        "prompt": "a cat dancing in the rain",
        "height": 512,
        "width": 512,
        "length": 24,
        "steps": 4,
    }
    from helpers import call_flash_comfy
    result = call_flash_comfy(data)
    verify_contract(result)
    verify_artifact_video(result["artifact"]["presigned_url"])


# --- Flash Ref2VA Comfy ---

@pytest.fixture(scope="module")
def flash_ref2va_comfy_deployed():
    deploy_flash_comfy()
    try:
        yield
    finally:
        undeploy_flash_comfy()


def test_e2e_dev_flash_ref2va_comfy_returns_contract_and_uploads_artifact(flash_ref2va_comfy_deployed):
    """generate() with good input -> returns output contract, R2 bucket has artifact."""
    data = {
        "prompt": "a cat dancing in the rain",
        "height": 512,
        "width": 512,
        "length": 24,
        "steps": 4,
    }
    from helpers import call_flash_comfy
    result = call_flash_comfy(data)
    verify_contract(result)
    verify_artifact_video(result["artifact"]["presigned_url"])


# --- Beam Ref2VA Comfy ---

@pytest.fixture(scope="module")
def beam_ref2va_comfy_deployment():
    deployment_id, endpoint_url, auth_token = deploy_beam_fl2va()
    try:
        yield deployment_id, endpoint_url, auth_token
    finally:
        undeploy_beam(deployment_id)


def test_e2e_dev_beam_ref2va_comfy_returns_contract_and_uploads_artifact(beam_ref2va_comfy_deployment):
    """generate() with good input -> returns output contract, R2 bucket has artifact."""
    deployment_id, endpoint_url, auth_token = beam_ref2va_comfy_deployment
    data = call_beam_fl2va(
        input_data={
            "prompt": "a cat dancing in the rain",
            "height": 512,
            "width": 512,
            "length": 24,
            "steps": 4,
        },
        endpoint_url=endpoint_url,
        auth_token=auth_token,
    )
    verify_contract(data)
    verify_artifact_video(data["artifact"]["presigned_url"])
