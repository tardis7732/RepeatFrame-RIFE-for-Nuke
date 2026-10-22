"""Repeat runs: first occurrence stays; later copies interpolate to next change."""
import math


def find_runs(first, last, differences, tolerance=0.0):
    if first > last or not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError('Invalid range or tolerance')
    runs, trailing = [], []
    anchor = first
    for frame in range(first + 1, last + 1):
        value = differences[frame]
        if not math.isfinite(value):
            raise ValueError('Non-finite difference at frame %d' % frame)
        if value > tolerance:
            if frame > anchor + 1:
                runs.append(dict(left=anchor, right=frame,
                                 start=anchor + 1, end=frame - 1))
            anchor = frame
    if anchor < last:
        trailing = list(range(anchor + 1, last + 1))
    return runs, trailing


def fraction(frame, run):
    return float(frame - run['left']) / (run['right'] - run['left'])
