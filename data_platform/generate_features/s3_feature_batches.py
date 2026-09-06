"""Immutable Parquet batch objects and the final consolidated file of a campaign feature.

Adds the Q44 provenance columns to label rows, validates the label subset and
the provenance columns separately, writes one ``batches/part-NNNNN.parquet``
object per completed chunk, and consolidates ``final.parquet`` once every
input id has a row.
"""

from __future__ import annotations


def attach_provenance():
    raise NotImplementedError


def validate_q44_rows():
    raise NotImplementedError


def write_batch():
    raise NotImplementedError


def adopt_unrecorded_batch():
    raise NotImplementedError


def read_batches():
    raise NotImplementedError


def labeled_ids():
    raise NotImplementedError


def consolidate_final():
    raise NotImplementedError
