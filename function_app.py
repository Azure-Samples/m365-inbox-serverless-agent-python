import logging

# Suppress noisy SDK HTTP traces so [TOOL] lines stand out in `func5 run` output.
# These three account for ~95% of the per-invocation log volume.
for noisy in (
    "azure.core.pipeline.policies.http_logging_policy",
    "azure.identity",
    "azure.identity.aio",
    "httpx",
    "httpcore",
    "urllib3",
):
    logging.getLogger(noisy).setLevel(logging.WARNING)

from azure_functions_agents import create_function_app  # noqa: E402

app = create_function_app()
