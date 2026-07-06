import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient


MLFLOW_TRACKING_URI = "sqlite:///mlops/mlflow.db"

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

client = MlflowClient()


def log_model_run(
    model_type: str,
    params: dict,
    metrics: dict,
    sklearn_model=None
):
    """
    Log experiment + register model
    """

    mlflow.set_experiment("AdaptiveSentinel")

    with mlflow.start_run():

        # log hyperparameters
        mlflow.log_params(params)

        # log metrics
        mlflow.log_metrics(metrics)

        # register sklearn model
        if sklearn_model is not None:

            mlflow.sklearn.log_model(
                sk_model=sklearn_model,
                name="sklearn_model",
                registered_model_name=model_type
            )

        run_id = mlflow.active_run().info.run_id

        print(f"[MLflow] Run logged: {run_id}")

        return run_id


def promote_model(
    model_name: str,
    version: int,
    stage: str = "Production"
):
    """
    Promote model version
    """

    client.transition_model_version_stage(
        name=model_name,
        version=version,
        stage=stage
    )

    print(
        f"[MLflow] {model_name} "
        f"v{version} promoted to {stage}"
    )


def get_production_model(
    model_name: str
):
    """
    Load production model
    """

    model_uri = f"models:/{model_name}/Production"

    model = mlflow.sklearn.load_model(
        model_uri
    )

    return model


def list_models():

    models = client.search_registered_models()

    return [
        (
            m.name,
            m.latest_versions
        )
        for m in models
    ]


if __name__ == "__main__":
    print(list_models())