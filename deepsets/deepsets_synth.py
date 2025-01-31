# Deepsets models in a format friendly for synthetisation. For more details on the
# architecture see the deepsets.py file.

import numpy as np

import tensorflow as tf
from tensorflow import keras
import tensorflow.keras.layers as KL
import qkeras


def deepsets_invariant_synth(
    input_shape: tuple = (150, 16),
    nnodes_phi: int = 32,
    nnodes_rho: int = 16,
    activ: str = "elu",
    nbits: int = 8,
):
    """
    Invariant deepsets network using functional API to be compatible with hls4ml.
    The details of this architecture can be found in deepsets.py.
    """

    nbits = format_quantiser(nbits)
    activ = format_qactivation(activ, nbits)
    nclasses = 5

    deepsets_input = keras.Input(shape=input_shape, name="input_layer")

    # Phi network.
    x_phi = qkeras.QDense(nnodes_phi, kernel_quantizer=nbits, bias_quantizer=nbits)(
        deepsets_input
    )
    x_phi = qkeras.QActivation(activ)(x_phi)

    x_phi = qkeras.QDense(nnodes_phi, kernel_quantizer=nbits, bias_quantizer=nbits)(
        x_phi
    )
    x_phi = qkeras.QActivation(activ)(x_phi)

    x_phi = qkeras.QDense(nnodes_phi, kernel_quantizer=nbits, bias_quantizer=nbits)(
        x_phi
    )
    phi_output = qkeras.QActivation(activ)(x_phi)

    # Invariant operation
    # inv_operation_output = KL.GlobalMaxPooling1D()(phi_output)
    inv_operation_output = KL.GlobalAveragePooling1D()(phi_output)

    # Rho network.
    x_rho = qkeras.QDense(nnodes_rho, kernel_quantizer=nbits, bias_quantizer=nbits)(
        inv_operation_output
    )
    x_rho = qkeras.QActivation(activ)(x_rho)

    deepsets_output = KL.Dense(nclasses)(x_rho)
    deepsets = keras.Model(deepsets_input, deepsets_output, name="deepsets_invariant")

    return deepsets


def deepsets_equivariant_synth(
    input_shape=(150, 16),
    nnodes_phi: int = 32,
    nnodes_rho: int = 16,
    activ: str = "elu",
    nbits: int = 8,
):
    """
    Equivariant deepsets network using functional API to be compatible with hls4ml.
    The details of this architecture can be found in deepsets.py.

    DOES NOT WORK YET SINCE GLOBALMAXPOOLING1D DOES NOT HAVE KEEPDIMS IN HLS4ML.
    """
    nbits = format_quantiser(nbits)
    activ = format_qactivation(activ, nbits)
    nclasses = 5

    deepsets_input = keras.Input(shape=input_shape, name="input_layer")

    # Permutation Equivariant Layer
    x_sum = KL.GlobalAveragePooling1D()(deepsets_input)
    # TODO~ KeepDims not supported in hls4ml, switch to extension API and new GP wrapper. Ask Katya about qkeras in contrib/
    x_lambd = qkeras.QDense(
        nnodes_phi, use_bias=False, kernel_quantizer=nbits, bias_quantizer=nbits
    )(x_sum)
    x_gamma = qkeras.QDense(nnodes_phi, kernel_quantizer=nbits, bias_quantizer=nbits)(
        deepsets_input
    )
    x = KL.Subtract()([x_gamma, x_lambd])
    x = qkeras.QActivation(activ)(x)

    # Permutation Equivariant Layer
    x_sum = KL.GlobalAveragePooling1D()(x)
    x_lambd = qkeras.QDense(
        nnodes_phi, use_bias=False, kernel_quantizer=nbits, bias_quantizer=nbits
    )(x_sum)
    x_gamma = qkeras.QDense(nnodes_phi, kernel_quantizer=nbits, bias_quantizer=nbits)(x)
    x = KL.Subtract()([x_gamma, x_lambd])
    x = qkeras.QActivation(activ)(x)

    # Permutation Equivariant Layer
    x_sum = KL.GlobalAveragePooling1D()(x)
    x_lambd = qkeras.QDense(
        nnodes_phi, use_bias=False, kernel_quantizer=nbits, bias_quantizer=nbits
    )(x_sum)
    x_gamma = qkeras.QDense(nnodes_phi, kernel_quantizer=nbits, bias_quantizer=nbits)(x)
    x = KL.Subtract()([x_gamma, x_lambd])
    x = qkeras.QActivation(activ)(x)

    x_sum = KL.GlobalAveragePooling1D()(x)
    x = qkeras.QDense(nnodes_rho, kernel_quantizer=nbits, bias_quantizer=nbits)(x)
    x = qkeras.QActivation(activ)(x)
    deepsets_output = KL.Dense(nclasses)(x)
    deepsets_network = keras.Model(
        deepsets_input, deepsets_output, name="deepsets_equivariant"
    )
    return deepsets_network


def format_quantiser(nbits: int):
    """Format the quantisation of the ml floats in a QKeras way."""
    if nbits == 1:
        return "binary(alpha=1)"
    elif nbits == 2:
        return "ternary(alpha=1)"
    else:
        return f"quantized_bits({nbits}, 0, alpha=1)"


def format_qactivation(activation: str, nbits: int) -> str:
    """Format the activation function strings in a QKeras friendly way."""
    return f"quantized_{activation}({nbits}, 0)"
