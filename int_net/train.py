# Training of the model defined in the model.py file.

import os

from tensorflow.keras import callbacks

from . import util
from .data import Data
from .model import QConvIntNet
from .terminal_colors import tcols

# Silence the info from tensorflow in which it brags that it can run on cpu nicely.
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"


def main(args):
    seed = 123
    outdir = "./trained_intnets/" + args["outdir"] + "/"
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    jet_data = Data.shuffled(
        args["data_folder"],
        args["data_hyperparams"],
        args["norm"],
        args["train_events"],
        0,
        seed=seed,
    )

    model = QConvIntNet(jet_data.tr_data.shape[1], jet_data.tr_data.shape[2])
    model.compile(**args["inet_hyperparams"]["compilation"])
    model.build(jet_data.tr_data.shape)
    model.summary(expand_nested=True)
    util.print_model_attributes(model, args)

    print(tcols.HEADER + "\nTraining the model... \U0001F4AA" + tcols.ENDC)
    callbacks = get_callbacks()
    model.fit(
        jet_data.tr_data,
        jet_data.tr_target,
        epochs=args["epochs"],
        batch_size=args["batch"],
        verbose=2,
        callbacks=callbacks,
        validation_split=0.3,
    )

    print(tcols.OKGREEN + "\nSaving model to: " + tcols.ENDC, outdir)
    model.save(outdir, save_format="tf")
    print(tcols.OKGREEN + "Done! \U0001F370\U00002728" + tcols.ENDC)


def get_callbacks():
    """Perpare the callbacks for the training."""
    early_stopping = callbacks.EarlyStopping(
        monitor="val_categorical_accuracy", patience=10
    )
    learning = callbacks.ReduceLROnPlateau(
        monitor="val_categorical_accuracy", factor=0.2, patience=10
    )

    return [early_stopping, learning]
