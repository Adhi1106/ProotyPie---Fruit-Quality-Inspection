from pathlib import Path

import pytest

from experiments.run_fruits360_experiment import activation_layer, make_model, split_train_validation


def test_split_is_stratified_disjoint_and_complete():
    records = [(Path(f"class_a/{i}.jpg"), "A", f"a{i}") for i in range(10)] + [
        (Path(f"class_b/{i}.jpg"), "B", f"b{i}") for i in range(10)
    ]
    train, validation = split_train_validation(records, validation_fraction=0.2, seed=7)
    assert len(train) == 16
    assert len(validation) == 4
    assert {r[2] for r in train}.isdisjoint({r[2] for r in validation})
    assert {r[1] for r in validation} == {"A", "B"}


@pytest.mark.parametrize("name", ["relu", "sigmoid", "tanh", "leaky_relu"])
def test_all_requested_activation_names_build(name):
    layer = activation_layer(name)
    assert layer is not None


def test_model_can_use_activation_twice_without_duplicate_names():
    model = make_model("relu", 0.01)
    assert model.input_shape == (None, 48, 48, 3)
    assert model.output_shape == (None, 4)


def test_unknown_activation_is_rejected():
    with pytest.raises(ValueError, match="Unsupported activation"):
        activation_layer("swish")
