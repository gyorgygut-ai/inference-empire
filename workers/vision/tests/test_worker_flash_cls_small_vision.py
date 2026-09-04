from workers.vision.testing import VISION_FLASH_CLS as SPEC


def test_generate_rejects_invalid_input(platform, runner, storage):
    worker = platform.create_worker(storage=storage)
    try:
        runner.run(worker, image_base64=None)
        assert False, "Should reject"
    except Exception as e:
        assert "image_base64" in str(e)


def test_generate_returns_output_contract_on_inference_failure(platform, runner, storage):
    worker = platform.create_worker(storage=storage)
    try:
        runner.run(
            worker,
            image_base64="failure",
        )
        assert False, "Should raise"
    except RuntimeError as e:
        assert "inference" in str(e)


def test_generate_returns_output_contract_on_inference_success(platform, runner, storage):
    result = runner.run(
        platform.create_worker(storage=storage),
        image_base64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR4nGNgAAIAAAUAAXpeqz8AAAAASUVORK5CYII=",
    )
    assert "classification" in result
    assert result["classification"] in [
        "portrait_0p",
        "portrait_1p",
        "portrait_2p",
        "portrait_3p",
        "portrait_group",
        "selfie_1p",
        "selfie_2p",
        "selfie_group",
        "group_photo_2p",
        "group_photo_3p",
        "group_photo_4p",
        "group_photo_5p_plus",
        "group_photo_group",
        "food_0p",
        "document_0p",
        "landscape_0p",
        "animal_0p",
        "object_0p",
        "screenshot_0p",
        "receipt_0p",
        "other_0p",
    ]
    assert "subjects" in result
    assert isinstance(result["subjects"], list)
    assert "description" in result
    assert isinstance(result["description"], str)
