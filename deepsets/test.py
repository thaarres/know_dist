# Loads a model and runs it on data it was not trained on.

import os
import json

# Silence the info from tensorflow in which it brags that it can run on cpu nicely.
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import numpy as np
import tensorflow as tf
from tensorflow import keras

# keras.utils.set_random_seed(123)

import util.util
import util.plots
import util.data
from . import flops
from util.terminal_colors import tcols

# Set keras float precision. Default is float32.
# tf.keras.backend.set_floatx("float64")


def main(args):
    util.util.device_info()
    plots_dir = util.util.make_output_directory(
        args["model_dir"], f"plots_{args['const_seed']}"
    )

    hyperparams = util.util.load_hyperparameters_file(args["model_dir"])
    hyperparams["data_hyperparams"].update(args["data_hyperparams"])

    data = util.data.Data(**hyperparams["data_hyperparams"])
    # data.test_data = shuffle_constituents(data.test_data, args)

    model = import_model(args, hyperparams)

    # FLOPs calculation only implemented for floating point models.
    if hyperparams['deepsets_type'] in ['equivariant', 'invariant']:
        nflops = flops.get_flops(model)
        print("\n".join(f"{k} FLOPs: {v}" for k, v in nflops.items()))
        print(f"{'':=<65}")

        nflops_tfgraph = flops.get_flops_tfgraph(args['model_dir'])
        print(f"TFGraph FLOPs: {nflops_tfgraph} \U0001fA74")

    exit(1)

    print(tcols.HEADER + f"\nRunning inference" + tcols.ENDC)
    y_pred = tf.nn.softmax(model.predict(data.test_data)).numpy()

    ce_loss = keras.losses.CategoricalCrossentropy()(data.test_target, y_pred)
    print(tcols.OKCYAN + f"\nCross-entropy loss: {ce_loss}" + tcols.ENDC)

    util.plots.roc_curves(plots_dir, y_pred, data.test_target)
    util.plots.dnn_output(plots_dir, y_pred)
    print(tcols.OKGREEN + "\nPlotting done! \U0001F4C8\U00002728" + tcols.ENDC)

    print(tcols.OKGREEN + "\nSaving the model weights..." + tcols.ENDC)
    weights_file_path = os.path.join(args["model_dir"], "model_weights.h5")
    model.save_weights(weights_file_path, save_format="h5")
    print(tcols.OKGREEN + "Saved predictions array..." + tcols.ENDC)
    y_pred.astype("float32").tofile(os.path.join(plots_dir, "y_pred.dat"))


def import_model(args: dict, hyperparams: dict):
    """Imports the model from a specified path. Model is saved in tf format."""
    print(tcols.HEADER + "Importing the model..." + tcols.ENDC)
    util.util.nice_print_dictionary("DS hps:", hyperparams["model_hyperparams"])
    model = keras.models.load_model(args["model_dir"], compile=False)
    model.summary(expand_nested=True)

    return model


def shuffle_constituents(data: np.ndarray, args: dict) -> np.ndarray:
    """Shuffles the constituents based on an array of seeds.

    Note that each jet's constituents is shuffled with respect to a seed that is fixed.
    This seed is different for each jet.
    """
    print("Shuffling constituents...")

    rng = np.random.default_rng(args["const_seed"])
    seeds = rng.integers(low=0, high=10000, size=data.shape[0])

    for jet_idx, seed in enumerate(seeds):
        shuffling = np.random.RandomState(seed=seed).permutation(data.shape[1])
        data[jet_idx, :] = data[jet_idx, shuffling]

    print(tcols.OKGREEN + f"Shuffling done! \U0001F0CF" + tcols.ENDC)

    return data

