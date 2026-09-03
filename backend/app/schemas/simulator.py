from pydantic import BaseModel, Field


class SimulatorInjectRequest(BaseModel):
    scenario_code: str = Field(examples=["SMT_TEMP_RISE_001"])
    sync: bool = True


class SimulatorStatusOut(BaseModel):
    running: bool
    sample_interval_seconds: int
    retention_days: int
    debounce_n: int
    active_scenarios: dict[str, str]
    last_tick_at: str | None = None
    last_alarm_id: int | None = None
    stop_pending: bool = False
