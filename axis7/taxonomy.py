"""Review records for proposed mappings; approval never validates model transfer."""
from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

CANDIDATES = {
    'rhythm':'Organisation relative des durées musicales.',
    'pitch_accuracy':'Conformité des hauteurs à une référence explicite.',
    'timing':'Écart temporel à des instants de référence.',
    'melodic_reproduction':'Ressemblance d’une séquence mélodique à sa référence.',
    'coordination':'Organisation conjointe de plusieurs actions musicales.',
    'technical_execution':'Réalisation d’un geste instrumental défini.',
    'consistency':'Stabilité de résultats comparables entre plusieurs essais.'}


class MappingReview(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source: Literal['singpad','amme','yousician']
    source_concept: str = Field(min_length=1,max_length=80)
    proposed_skill: Literal['rhythm','pitch_accuracy','timing','melodic_reproduction','coordination','technical_execution','consistency']
    definition: str = Field(min_length=20,max_length=2000)
    supporting_evidence: list[str] = Field(min_length=1,max_length=20)
    version: str = Field(pattern=r'^[a-zA-Z0-9_.-]{1,40}$')
    status: Literal['proposed','pending_review','approved','rejected']
    reviewer: str | None = Field(default=None,max_length=120)
    reviewer_qualification: str | None = Field(default=None,max_length=500)
    approval_date: date | None = None

    @model_validator(mode='after')
    def actual_review(self):
        if self.status=='approved':
            if not self.reviewer or not self.reviewer_qualification or not self.approval_date or self.approval_date>date.today():
                raise ValueError('Approval requires dated qualified reviewer and evidence')
        elif self.approval_date is not None: raise ValueError('Unapproved mapping cannot have approval date')
        return self


def approved_mappings(records):
    return [MappingReview(**r).model_dump(mode='json') for r in records if MappingReview(**r).status=='approved']
