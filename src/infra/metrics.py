from collections import defaultdict
from dataclasses import dataclass, field
from threading import RLock
from time import monotonic, time
from typing import Dict


LabelMap = Dict[str, str]
MetricKey = tuple[str, tuple[tuple[str, str], ...]]


def _to_key(name: str, labels: LabelMap | None) -> MetricKey:
    if not labels:
        return name, tuple()
    return name, tuple(sorted((str(k), str(v)) for k, v in labels.items()))


def _labels_from_key(key: MetricKey) -> LabelMap:
    _, labels = key
    return {k: v for k, v in labels}


def _label_text(labels: LabelMap) -> str:
    if not labels:
        return ""
    escaped = [
        f'{key}="{str(value).replace("\\", "\\\\").replace(chr(34), "\\\"")}"'
        for key, value in sorted(labels.items())
    ]
    return "{" + ",".join(escaped) + "}"


def _as_counter_row(metric: "_ScalarMetric") -> tuple[str, float, str]:
    return metric.name, metric.value, _label_text(metric.labels)


def _as_gauge_row(metric: "_ScalarMetric") -> tuple[str, float, str]:
    return metric.name, metric.value, _label_text(metric.labels)


def _as_histogram_rows(name: str, metric: "_HistogramMetric") -> list[tuple[str, float, str]]:
    return [
        (f"{name}_count", metric.count, _label_text(metric.labels)),
        (f"{name}_sum", metric.sum, _label_text(metric.labels)),
    ]


@dataclass
class _ScalarMetric:
    name: str
    value: float = 0.0
    labels: LabelMap = field(default_factory=dict)


@dataclass
class _HistogramMetric:
    name: str
    count: int = 0
    sum: float = 0.0
    labels: LabelMap = field(default_factory=dict)


_lock = RLock()
_counters: Dict[MetricKey, _ScalarMetric] = {}
_gauges: Dict[MetricKey, _ScalarMetric] = {}
_histograms: Dict[MetricKey, _HistogramMetric] = {}


def inc_counter(name: str, value: float = 1.0, labels: LabelMap | None = None) -> None:
    """Increase a named counter metric."""
    key = _to_key(name, labels)
    with _lock:
        metric = _counters.get(key)
        if metric is None:
            metric = _ScalarMetric(name=name, labels=_labels_from_key(key))
            _counters[key] = metric
        metric.value += value


def observe_ms(name: str, value_ms: float, labels: LabelMap | None = None) -> None:
    """Record a duration-like value."""
    key = _to_key(name, labels)
    with _lock:
        metric = _histograms.get(key)
        if metric is None:
            metric = _HistogramMetric(name=name, labels=_labels_from_key(key))
            _histograms[key] = metric
        metric.count += 1
        metric.sum += value_ms


def set_gauge(name: str, value: float, labels: LabelMap | None = None) -> None:
    """Set a named gauge metric."""
    key = _to_key(name, labels)
    with _lock:
        metric = _gauges.get(key)
        if metric is None:
            metric = _ScalarMetric(name=name, labels=_labels_from_key(key))
            _gauges[key] = metric
        metric.value = value


def inc_gauge(name: str, delta: float = 1.0, labels: LabelMap | None = None) -> None:
    """Increase or decrease a gauge metric."""
    key = _to_key(name, labels)
    with _lock:
        metric = _gauges.get(key)
        if metric is None:
            metric = _ScalarMetric(name=name, labels=_labels_from_key(key))
            _gauges[key] = metric
        metric.value += delta


def snapshot() -> Dict:
    """Return a snapshot suitable for metrics endpoint payload."""
    with _lock:
        return {
            "timestamp": time(),
            "counters": [
                {"name": name, "value": value, "labels": labels}
                for name, value, labels in (_as_counter_row(m) for m in _counters.values())
            ],
            "gauges": [
                {"name": name, "value": value, "labels": labels}
                for name, value, labels in (_as_gauge_row(m) for m in _gauges.values())
            ],
            "histograms": [
                {"name": metric.name, "count": metric.count, "sum": metric.sum, "labels": metric.labels}
                for metric in _histograms.values()
            ],
        }


def prom_text() -> str:
    """Export in Prometheus text format."""
    with _lock:
        lines: list[str] = []

        grouped_counters: dict[str, list[tuple[str, float, str]]]=defaultdict(list)
        for metric in _counters.values():
            grouped_counters[metric.name].append(_as_counter_row(metric))

        grouped_gauges: dict[str, list[tuple[str, float, str]]] = defaultdict(list)
        for metric in _gauges.values():
            grouped_gauges[metric.name].append(_as_gauge_row(metric))

        grouped_histograms: dict[str, list[tuple[str, float, str]]] = defaultdict(list)
        for metric in _histograms.values():
            for row in _as_histogram_rows(metric.name, metric):
                grouped_histograms[metric.name].append(row)

        for name, samples in grouped_counters.items():
            lines.append(f"# HELP {name} {name}")
            lines.append(f"# TYPE {name} counter")
            for sample_name, value, labels in samples:
                lines.append(f"{sample_name}{labels} {value}")

        for name, samples in grouped_gauges.items():
            lines.append(f"# HELP {name} {name}")
            lines.append(f"# TYPE {name} gauge")
            for sample_name, value, labels in samples:
                lines.append(f"{sample_name}{labels} {value}")

        for name, samples in grouped_histograms.items():
            lines.append(f"# HELP {name} {name}")
            lines.append(f"# TYPE {name} histogram")
            for sample_name, value, labels in samples:
                lines.append(f"{sample_name}{labels} {value}")

        if not lines:
            return ""

        return "\n".join(lines) + "\n"


def reset() -> None:
    """Reset counters for test/dev usage."""
    with _lock:
        _counters.clear()
        _gauges.clear()
        _histograms.clear()


def _metric_key(name: str, labels: LabelMap | None) -> str:
    return f"{name}{_label_text(labels or {})}"


def _split_metric_key(full_name: str) -> tuple[str, str]:
    if "{" not in full_name or not full_name.endswith("}"):
        return full_name, ""
    name, label_part = full_name.split("{", 1)
    label_part = label_part[:-1]
    return name, label_part


def debug_summary() -> dict[str, float]:
    """Compatibility helper for dashboards and health checks."""
    counters = defaultdict(float)
    gauges = defaultdict(float)
    hist = defaultdict(float)

    with _lock:
        for metric in _counters.values():
            counters[metric.name] += metric.value
        for metric in _gauges.values():
            gauges[metric.name] += metric.value
        for metric in _histograms.values():
            hist[f"{metric.name}_count"] += metric.count
            hist[f"{metric.name}_sum"] += metric.sum

    return {
        "uptime_seconds": monotonic(),
        **{f"counter.{key}": value for key, value in counters.items()},
        **{f"gauge.{key}": value for key, value in gauges.items()},
        **{f"histogram.{key}": value for key, value in hist.items()},
    }
