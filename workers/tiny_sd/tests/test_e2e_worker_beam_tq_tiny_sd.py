def test_beam_generate_returns_image_artifact():
    import workers.tiny_sd.worker_beam_tq_tiny_sd as worker_mod

    task = worker_mod.dispatch.put({"prompt": "a red square", "seed": 7})
    result = task.result(wait=True)
    assert result is not None, f"Task {getattr(task, 'id', 'unknown')} returned None - check beam logs"
    assert "artifact" in result
    assert "presigned_url" in result["artifact"]
