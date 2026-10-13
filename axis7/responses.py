"""Stable public forecast envelope; probabilities concern binary performance only."""
from typing import Literal
from pydantic import BaseModel,ConfigDict
from .schema import UnitFloat

class ForecastV2(BaseModel):
    model_config=ConfigDict(extra='forbid')
    response_version:Literal['2.0']='2.0'
    student_id:str
    domain:Literal['music-mock','forget-se']
    model_id:str
    exercise_id:str|None
    conditioning:Literal['exercise','generic_skill']
    item_supported:bool|None
    training_provenance:Literal['synthetic','public_software_engineering']
    probabilities:dict[str,UnitFloat]
    warning:str
