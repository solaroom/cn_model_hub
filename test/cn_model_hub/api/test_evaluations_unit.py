"""Unit tests for quick evaluation helpers."""

from cn_model_hub.api.evaluations import EVAL_SCRIPT, _evaluation_tasks


def test_eval_script_filters_token_type_ids_before_generate():
    pop_index = EVAL_SCRIPT.index('inputs.pop("token_type_ids", None)')
    generate_index = EVAL_SCRIPT.index("generated = model.generate(")

    assert pop_index < generate_index


def test_eval_script_prefers_dtype_with_torch_dtype_fallback():
    dtype_index = EVAL_SCRIPT.index("dtype=torch.float32")
    fallback_index = EVAL_SCRIPT.index("torch_dtype=torch.float32")

    assert dtype_index < fallback_index
    assert 'if "dtype" not in str(exc):' in EVAL_SCRIPT


def test_evaluation_tasks_are_retained_until_completion():
    assert isinstance(_evaluation_tasks, set)
