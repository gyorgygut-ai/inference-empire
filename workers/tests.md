uv run --locked pytest workers/vision/tests/test_e2e_worker_beam_tq_small_vision.py -v &&
uv run --locked pytest workers/vision/tests/test_e2e_worker_flash_cls_small_vision.py -v &&
uv run --locked pytest workers/vision/tests/test_e2e_worker_modal_cls_small_vision.py -v &&

uv run --locked pytest workers/tiny_sd/tests/test_e2e_worker_beam_tq_tiny_sd.py -v &&
uv run --locked pytest workers/tiny_sd/tests/test_e2e_worker_flash_cls_tiny_sd.py -v &&
uv run --locked pytest workers/tiny_sd/tests/test_e2e_worker_modal_cls_tiny_sd.py -v &&

uv run --locked pytest workers/flux2/tests/test_e2e_worker_beam_tq_flux2_klein9b.py -v &&
uv run --locked pytest workers/flux2/tests/test_e2e_worker_flash_cls_flux2_klein9b.py -v &&
uv run --locked pytest workers/flux2/tests/test_e2e_worker_modal_cls_flux2_klein9b.py -v &&

uv run --locked pytest workers/krea2/tests/test_e2e_worker_beam_tq_krea2_ref2img.py -v &&
uv run --locked pytest workers/krea2/tests/test_e2e_worker_flash_cls_krea2_ref2img.py -v &&
uv run --locked pytest workers/krea2/tests/test_e2e_worker_modal_cls_krea2_ref2img.py -v &&

uv run --locked pytest workers/h3/tests/test_e2e_worker_beam_tq_minimax_h3_comfy.py -v &&
uv run --locked pytest workers/h3/tests/test_e2e_worker_flash_cls_minimax_h3_comfy.py -v &&
uv run --locked pytest workers/h3/tests/test_e2e_worker_modal_cls_minimax_h3_comfy.py -v &&

uv run --locked pytest workers/h3/tests/test_e2e_worker_beam_tq_minimax_h3_fl2va.py -v &&
uv run --locked pytest workers/h3/tests/test_e2e_worker_flash_cls_minimax_h3_fl2va.py -v &&
uv run --locked pytest workers/h3/tests/test_e2e_worker_modal_cls_minimax_h3_fl2va.py -v &&

uv run --locked pytest workers/h3/tests/test_e2e_worker_beam_tq_minimax_h3_ref2va.py -v &&
uv run --locked pytest workers/h3/tests/test_e2e_worker_flash_cls_minimax_h3_ref2va.py -v &&
uv run --locked pytest workers/h3/tests/test_e2e_worker_modal_cls_minimax_h3_ref2va.py -v &&

uv run --locked pytest workers/h3/tests/test_e2e_worker_beam_tq_minimax_h3_ref2va_comfy.py -v &&
uv run --locked pytest workers/h3/tests/test_e2e_worker_flash_pre_minimax_h3_ref2va_comfy.py -v &&
uv run --locked pytest workers/h3/tests/test_e2e_worker_modal_cls_minimax_h3_ref2va_comfy.py -v &&
