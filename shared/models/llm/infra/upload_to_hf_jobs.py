"""Submit a Docker image and its run settings to Hugging Face Jobs.

Jobs pulls ``image`` from a registry. ``upload_to_hf_jobs`` sends that
reference together with the hardware, command, environment, and secrets.
Pass ``push=True`` after a local ``docker build`` of the same tag so the
registry has the image before the job starts. A Docker Space image
(``hf.co/spaces/<namespace>/<space>``) is already hosted, so leave
``push`` false for those.

Call it from an experiment after the image exists:

    upload_to_hf_jobs(
        "docker.io/<namespace>/my-image:latest",
        HuggingFaceJobConfig(
            command=("python", "train.py"),
            flavor="a10g-large",
            timeout="24h",
        ),
        push=True,
    )
"""

from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from huggingface_hub import JobInfo, run_job

_SPACE_IMAGE_PREFIXES = (
    "hf.co/spaces/",
    "huggingface.co/spaces/",
    "https://hf.co/spaces/",
    "https://huggingface.co/spaces/",
)


@dataclass(frozen=True)
class HuggingFaceJobConfig:
    """Settings submitted with the image.

    ``command`` is the process Jobs runs inside the image. ``flavor`` is a
    Jobs hardware name such as ``a10g-large``. ``timeout`` uses the Jobs
    duration form, for example ``24h``. ``secrets`` are encrypted job
    environment variables.
    """

    command: Sequence[str]
    flavor: str = "cpu-basic"
    timeout: str | None = None
    env: Mapping[str, str] = field(default_factory=dict)
    secrets: Mapping[str, str] = field(default_factory=dict)
    namespace: str | None = None
    labels: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        command = tuple(self.command)
        if not command or any(not str(part).strip() for part in command):
            raise ValueError("command must contain at least one non-empty argument.")
        if not self.flavor or not self.flavor.strip():
            raise ValueError("flavor must be a non-empty hardware flavor.")
        object.__setattr__(self, "command", command)
        object.__setattr__(self, "env", dict(self.env))
        object.__setattr__(self, "secrets", dict(self.secrets))
        object.__setattr__(self, "labels", dict(self.labels))


def upload_to_hf_jobs(
    image: str,
    config: HuggingFaceJobConfig,
    *,
    push: bool = False,
) -> JobInfo:
    """Push ``image`` when requested, then start a Job with ``config``.

    Parameters
    ----------
    image
        Image reference Jobs will pull, for example
        ``docker.io/<namespace>/my-image:latest`` or
        ``hf.co/spaces/<namespace>/<space>``.
    config
        Command, hardware, timeout, environment, and secrets.
    push
        When true, ``docker push`` ``image`` before creating the Job.
        The tag must already exist in the local Docker daemon.

    Returns
    -------
    JobInfo
        The created job. ``url`` is the Hub page for the run.
    """
    reference = image.strip()
    if not reference:
        raise ValueError("image must be a non-empty Docker image reference.")
    if push:
        _push_image(reference)
    return run_job(
        image=reference,
        command=list(config.command),
        env=dict(config.env) or None,
        secrets=dict(config.secrets) or None,
        flavor=config.flavor,  # type: ignore[arg-type]
        timeout=config.timeout,
        labels=dict(config.labels) or None,
        namespace=config.namespace,
    )


def _push_image(image: str) -> None:
    """Publish ``image`` so Jobs can pull the tag this machine built."""
    if image.startswith(_SPACE_IMAGE_PREFIXES):
        raise ValueError(
            "Docker Space images are already hosted on the Hub. "
            f"Do not push {image!r}."
        )
    repository = image.split("@", 1)[0].split(":", 1)[0]
    if "/" not in repository:
        raise ValueError(
            "A pushed image needs a registry name, for example "
            "'docker.io/<namespace>/lora-finetuning-study2-2026-10-04:latest'. "
            f"Got {image!r}."
        )
    subprocess.run(["docker", "push", image], check=True)
