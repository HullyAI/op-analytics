from op_analytics.coreutils.duckdb_inmem import init_client
from op_analytics.coreutils.logger import (
    bind_contextvars,
    bound_contextvars,
    structlog,
)
from op_analytics.coreutils.partitioned.location import DataLocation
from op_analytics.coreutils.partitioned.output import OutputData

from .construct import construct_tasks
from .modelexecute import PythonModelExecutor
from .registry import REGISTERED_INTERMEDIATE_MODELS, load_model_definitions
from .task import IntermediateModelsTask
from .udfs import create_duckdb_macros

log = structlog.get_logger()


@bound_contextvars(pipeline_step="compute_intermediate")
def compute_intermediate(
    chains: list[str],
    models: list[str],
    range_spec: str,
    read_from: DataLocation,
    write_to: DataLocation,
    dryrun: bool,
    force_complete: bool = False,
):
    # Load python functions that define registered data models.
    load_model_definitions()

    for model in models:
        should_exit = False
        if model not in REGISTERED_INTERMEDIATE_MODELS:
            should_exit = True
            log.error(f"Model is not registered: {model}")
        if should_exit:
            log.error("Cannot run on unregistered models. Will exit.")
            exit(1)

    tasks = construct_tasks(chains, models, range_spec, read_from, write_to)

    if dryrun:
        log.info("DRYRUN: No work will be done.")
        return

    success = 0
    for i, task in enumerate(tasks):
        bind_contextvars(
            task=f"{i+1}/{len(tasks)}",
            **task.data_reader.partitions_dict(),
        )

        # Decide if we need to run this task.
        if task.data_writer.is_complete() and not force_complete:
            log.info("task", status="already_complete")
            continue

        # Decide if we can run this task.
        if not task.data_reader.inputs_ready:
            log.warning("task", status="input_not_ready")
            continue

        if force_complete:
            log.info("forced execution despite complete marker")
            task.data_writer.force = True

        try:
            executor(task)
        except Exception as ex:
            log.error("task", status="exception")
            log.error("intermediate model exception", exc_info=ex)
        else:
            log.info("task", status="success")

        success += 1


def executor(task: IntermediateModelsTask) -> None:
    """Execute the model computations."""

    # Load shared DuckDB UDFs.
    client = init_client()
    create_duckdb_macros(client)

    for model_name in task.models:
        # Get the model.
        im_model = REGISTERED_INTERMEDIATE_MODELS[model_name]

        with PythonModelExecutor(im_model, client, task.data_reader) as m:
            with bound_contextvars(model=model_name):
                log.info("running model")
                model_results = m.execute()

                produced_datasets = set(model_results.keys())
                if produced_datasets != set(im_model.expected_output_datasets):
                    raise RuntimeError(
                        f"model {model_name!r} produced unexpected datasets: {produced_datasets}"
                    )

                for result_name, rel in model_results.items():
                    task.data_writer.write(
                        output_data=OutputData(
                            dataframe=rel.pl(),
                            root_path=f"intermediate/{model_name}/{result_name}",
                            default_partition=task.data_reader.partitions_dict(),
                        ),
                    )
