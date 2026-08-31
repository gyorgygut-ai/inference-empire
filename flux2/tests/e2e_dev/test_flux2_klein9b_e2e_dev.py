"""E2E dev tests for flux2 workers.

Per TEST_CHECKLIST.md: "Test code deploys test worker before all; undeploys after all."
Deploys each worker via CLI, calls the endpoint via SDK, verifies contract + R2 artifact.
"""
import pytest

from helpers import (
    call_beam,
    call_modal,
    deploy_beam,
    deploy_modal,
    undeploy_beam,
    undeploy_modal,
    verify_artifact,
    verify_contract,
)


# --- Beam ---

@pytest.fixture(scope="module")
def beam_deployment():
    deployment_id = deploy_beam()
    try:
        yield deployment_id
    finally:
        undeploy_beam(deployment_id)


def test_e2e_dev_beam_returns_contract_and_uploads_artifact(beam_deployment):
    """generate() with good input -> returns output contract, R2 bucket has artifact."""
    data = call_beam(beam_deployment, input_data={
        "prompt": "a cat",
        "height": 512,
        "width": 512,
        "guidance_scale": 1.0,
        "num_inference_steps": 4,
    })
    verify_contract(data)
    verify_artifact(data["artifact"]["url"])


# --- Modal ---

@pytest.fixture(scope="module")
def modal_deployed():
    deploy_modal()
    try:
        yield
    finally:
        undeploy_modal()


def test_e2e_dev_modal_returns_contract_and_uploads_artifact(modal_deployed):
    """generate_web() with good input -> returns output contract, R2 bucket has artifact."""
    data = call_modal({
        "prompt": "a cat",
        "height": 512,
        "width": 512,
        "guidance_scale": 1.0,
        "num_inference_steps": 4,
    })
    verify_contract(data)
    verify_artifact(data["artifact"]["url"])
