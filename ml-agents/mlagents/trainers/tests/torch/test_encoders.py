import torch
from unittest import mock
import pytest

from mlagents.trainers.torch.encoders import (
    VectorEncoder,
    VectorAndUnnormalizedInputEncoder,
    Normalizer,
    SimpleVisualEncoder,
    ResNetVisualEncoder,
    NatureVisualEncoder,
)


# This test will also reveal issues with states not being saved in the state_dict.
def compare_models(module_1, module_2):
    is_same = True
    for key_item_1, key_item_2 in zip(
        module_1.state_dict().items(), module_2.state_dict().items()
    ):
        # Compare tensors in state_dict and not the keys.
        is_same = torch.equal(key_item_1[1], key_item_2[1]) and is_same
    return is_same


def test_normalizer():
    input_size = 2
    norm = Normalizer(input_size)

    # These three inputs should mean to 0.5, and variance 2
    # with the steps starting at 1
    vec_input1 = torch.tensor([[1, 1]])
    vec_input2 = torch.tensor([[1, 1]])
    vec_input3 = torch.tensor([[0, 0]])
    norm.update(vec_input1)
    norm.update(vec_input2)
    norm.update(vec_input3)

    # Test normalization
    for val in norm(vec_input1)[0]:
        assert val == pytest.approx(0.707, abs=0.001)

    # Test copy normalization
    norm2 = Normalizer(input_size)
    assert not compare_models(norm, norm2)
    norm2.copy_from(norm)
    assert compare_models(norm, norm2)
    for val in norm2(vec_input1)[0]:
        assert val == pytest.approx(0.707, abs=0.001)


@mock.patch("mlagents.trainers.torch.encoders.Normalizer")
def test_vector_encoder(mock_normalizer):
    mock_normalizer_inst = mock.Mock()
    mock_normalizer.return_value = mock_normalizer_inst
    input_size = 64
    hidden_size = 128
    num_layers = 3
    normalize = False
    vector_encoder = VectorEncoder(input_size, hidden_size, num_layers, normalize)
    output = vector_encoder(torch.ones((1, input_size)))
    assert output.shape == (1, hidden_size)

    normalize = True
    vector_encoder = VectorEncoder(input_size, hidden_size, num_layers, normalize)
    new_vec = torch.ones((1, input_size))
    vector_encoder.update_normalization(new_vec)

    mock_normalizer.assert_called_with(input_size)
    mock_normalizer_inst.update.assert_called_with(new_vec)

    vector_encoder2 = VectorEncoder(input_size, hidden_size, num_layers, normalize)
    vector_encoder.copy_normalization(vector_encoder2)
    mock_normalizer_inst.copy_from.assert_called_with(mock_normalizer_inst)


@mock.patch("mlagents.trainers.torch.encoders.Normalizer")
def test_vector_and_unnormalized_encoder(mock_normalizer):
    mock_normalizer_inst = mock.Mock()
    mock_normalizer.return_value = mock_normalizer_inst
    input_size = 64
    unnormalized_size = 32
    hidden_size = 128
    num_layers = 3
    normalize = True
    mock_normalizer_inst.return_value = torch.ones((1, input_size))
    vector_encoder = VectorAndUnnormalizedInputEncoder(
        input_size, hidden_size, unnormalized_size, num_layers, normalize
    )
    # Make sure normalizer is only called on input_size
    mock_normalizer.assert_called_with(input_size)
    normal_input = torch.ones((1, input_size))

    unnormalized_input = torch.ones((1, 32))
    output = vector_encoder(normal_input, unnormalized_input)
    mock_normalizer_inst.assert_called_with(normal_input)
    assert output.shape == (1, hidden_size)


@pytest.mark.parametrize("image_size", [(36, 36, 3), (84, 84, 4), (256, 256, 5)])
@pytest.mark.parametrize(
    "vis_class", [SimpleVisualEncoder, ResNetVisualEncoder, NatureVisualEncoder]
)
def test_visual_encoder(vis_class, image_size):
    num_outputs = 128
    enc = vis_class(image_size[0], image_size[1], image_size[2], num_outputs)
    # Note: NCHW not NHWC
    sample_input = torch.ones((1, image_size[2], image_size[0], image_size[1]))
    encoding = enc(sample_input)
    assert encoding.shape == (1, num_outputs)
