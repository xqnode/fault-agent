from fastapi import APIRouter, HTTPException

from app.schemas.common import ApiResponse
from app.schemas.simulator import SimulatorInjectRequest
from app.simulator.device_simulator import get_simulator

router = APIRouter(prefix="/simulator", tags=["simulator"])


@router.get("/status", response_model=ApiResponse)
def get_status():
    status = get_simulator().status()
    return ApiResponse(data=status.__dict__)


@router.post("/start", response_model=ApiResponse)
def post_start():
    try:
        status = get_simulator().start()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ApiResponse(data=status.__dict__)


@router.post("/stop", response_model=ApiResponse)
def post_stop():
    status = get_simulator().stop()
    return ApiResponse(data=status.__dict__)


@router.post("/inject", response_model=ApiResponse)
def post_inject(payload: SimulatorInjectRequest):
    try:
        result = get_simulator().inject(payload.scenario_code, sync=payload.sync)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ApiResponse(data=result)


@router.post("/reset", response_model=ApiResponse)
def post_reset():
    try:
        result = get_simulator().reset()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ApiResponse(data=result)
