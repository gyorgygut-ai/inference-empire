"""Beam local fake: in-process dict of zero-arg thunks."""

from __future__ import annotations

JOBS = {}


def submit(call):
    tid = f"beam-task-{len(JOBS)}"
    JOBS[tid] = call
    return tid


def poll(tid):
    return "COMPLETED" if tid in JOBS else "UNKNOWN"


def result(tid):
    return JOBS.pop(tid)()


def clear():
    JOBS.clear()
