"""Fault injection scenarios for demo / acceptance."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    code: str
    device_code: str
    metric_name: str
    trajectory: tuple[float, ...]
    expected_alarm_type: str
    # baselines for other metrics while primary metric follows trajectory
    baseline_temperature: float = 72.0
    baseline_pressure: float = 1.15
    baseline_vibration: float = 0.35
    baseline_power: float = 2.4


SCENARIOS: dict[str, Scenario] = {
    # 文档示例：72→75→82→91→98；为满足防抖 N=3，在超限段补一点 94
    "SMT_TEMP_RISE_001": Scenario(
        code="SMT_TEMP_RISE_001",
        device_code="SMT-001",
        metric_name="temperature",
        trajectory=(72.0, 75.0, 82.0, 91.0, 94.0, 98.0),
        expected_alarm_type="TEMPERATURE_HIGH",
        baseline_temperature=72.0,
        baseline_pressure=1.15,
        baseline_vibration=0.35,
        baseline_power=2.4,
    ),
}


def get_scenario(code: str) -> Scenario:
    scenario = SCENARIOS.get(code)
    if not scenario:
        known = ", ".join(sorted(SCENARIOS))
        raise KeyError(f"unknown scenario_code={code}; known=[{known}]")
    return scenario
