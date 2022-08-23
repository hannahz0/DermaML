#!/usr/bin/env python
"""
Script for running AutoML evaluation.
"""

# --- Imports

# Standard library
import csv
import json
import os
from pathlib import Path

# External packages
import pandas as pd
from pycaret import classification
import typer
import yaml


# --- Main program

def main(data_dir: Path,
         metadata_file: Path = "metadata.csv",
         best_models_file: Path = typer.Option("automl-best-models.yaml",
                                               "-m", "--models"),
         scores_file: Path = typer.Option("automl-scores.csv",
                                          "-s", "--scores"),
         num_best_models: int = 5,
         experiment_name: str = "automl",
         ) -> None:
    """
    Run AutoML evaluation.

    Results are output two files: 'model-scores.csv'
    """
    # --- Check arguments

    if not os.path.isdir(data_dir):
        typer.echo(f"data_dir` '{data_dir}' not found", err=True)
        raise typer.Abort()

    metadata_path = os.path.join(data_dir, metadata_file)
    if not os.path.isfile(metadata_path):
        typer.echo(
            f"metadata-file '{metadata_file}' not found in data_dir`",
            err=True)
        raise typer.Abort()

    if num_best_models <= 0:
        typer.echo(
            "num-best-models must be strictly positive",
            err=True)
        raise typer.Abort()

    # --- Preparations

    # Read metadata
    metadata_df = pd.read_csv(metadata_path)

    # Construct columns for features
    data_file = metadata_df.at[0, "file"]
    with open(os.path.join(data_dir, data_file), 'r') as data_path:
        features = json.load(data_path)
        texture_features = features["texture"]
        feature_columns = [f"texture-{i}"
                           for i in range(len(texture_features))]

    # Load features
    records = []
    for _, row in metadata_df.iterrows():
        # Read features from JSON
        with open(os.path.join(data_dir, row["file"]), 'r') as file_:
            features = json.load(file_)

        # Extract textures
        texture_features = features["texture"]

        # Add new record
        records.append(dict(zip(feature_columns, texture_features)))

    features_df = pd.DataFrame.from_records(records, columns=feature_columns)

    # Construct DataFrame for model training and testing
    data_df = features_df.merge(metadata_df, left_index=True, right_index=True)
    del data_df["file"]

    # --- Perform AutoML evaluation

    # Set up the dataset for AutoML
    classification.setup(data=data_df,
                         target="target",
                         log_experiment=True,
                         experiment_name=experiment_name,
                         html=False,
                         silent=True,
                         verbose=False)

    # Automatically train, test, and evaluate models
    best_models = classification.compare_models(n_select=num_best_models,
                                                verbose=False)

    # --- Save results

    # Best models
    best_models = [' '.join(s.strip() for s in str(model).split('\n'))
                   for model in best_models]
    with open(best_models_file, 'w') as file_:
        yaml.dump(best_models, file_, width=float("inf"))

    # Model scores
    classification.pull().to_csv(scores_file, index=False,
                                 quoting=csv.QUOTE_NONNUMERIC)


# --- Run app

if __name__ == "__main__":
    typer.run(main)
