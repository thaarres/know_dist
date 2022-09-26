# Tune the temperature and alpha of the distiller using keras tuner.

import os

import keras_tuner as kt
import tensorflow as tf
from tensorflow import keras

import intnets.util
import intnets.plots
from intnets.data import Data
from . import util
from .distiller import Distiller
from .distiller_hypermodel import DistillerHypermodel
from .terminal_colors import tcols

# Silence the info from tensorflow in which it brags that it can run on cpu nicely.
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
tf.keras.backend.set_floatx("float64")


def main(args):
    intnets.util.device_info()
    outdir = intnets.util.make_output_directory("trained_students", args["outdir"])

    data_hp = args["data_hyperparams"]
    intnets.util.nice_print_dictionary("DATA DEETS", data_hp)
    jet_data = Data(**data_hp, seed=args["seed"], jet_seed=args["jet_seed"])

    print("Importing the teacher network model...")
    teacher = keras.models.load_model(args["teacher"], compile=False)

    print(f"Instantiating the student of type: {args['student_type']}...")
    student = util.choose_student(args["student_type"], args["student"])

    print("Making the distiller...")
    args["distill"]["optimizer"] = intnets.util.choose_optimiser(
        args["distill"]["optimizer"], args["training_hyperparams"]["lr"]
    )
    distiller_hyperparams = args["distill"]
    distiller = Distiller(student, teacher)
    distiller_hypermodel = DistillerHypermodel(distiller, distiller_hyperparams)

    print(tcols.HEADER + "\nRUNNING THE OPTIMISATION \U0001F4AA" + tcols.ENDC)
    print("====================")
    tuner = kt.RandomSearch(
        distiller_hypermodel,
        objective="val_acc",
        max_trials=300,
        executions_per_trial=1,
        overwrite=True,
        directory=outdir,
    )
    tuner.search_space_summary()

    training_hyperparams = args["training_hyperparams"]
    util.print_training_attributes(training_hyperparams, distiller)
    tuner.search(
        jet_data.tr_data,
        jet_data.tr_target,
        epochs=training_hyperparams["epochs"],
        batch_size=training_hyperparams["batch"],
        verbose=2,
        callbacks=get_callbacks(),
        validation_split=0.3,
    )
    tuner.results_summary()


def get_callbacks():
    """Prepare the callbacks for the training."""
    early_stopping = keras.callbacks.EarlyStopping(monitor="val_acc", patience=20)
    learning = keras.callbacks.ReduceLROnPlateau(
        monitor="val_acc", factor=0.8, patience=10
    )

    return [early_stopping, learning]
