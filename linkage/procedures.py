from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ProcedureRule:
    procedure_id: str
    patterns: tuple[str, ...]


# This vocabulary is intentionally small and product-facing. It normalizes the
# procedures actually present in the GBG snapshot rather than attempting to be
# a comprehensive cosmetic-procedure ontology.
PROCEDURE_RULES: tuple[ProcedureRule, ...] = (
    ProcedureRule(
        "rhinoplasty",
        (
            r"\brhinoplast(?:y|ies)\b",
            r"\bnasal surgery\b",
            r"\bnose surgery\b",
            r"\bnose procedures?\b",
        ),
    ),
    ProcedureRule(
        "alar_reduction",
        (
            r"\balar reduction\b",
            r"\bnostril reduction\b",
            r"\balar lift\b",
            r"\balar angle correction\b",
        ),
    ),
    ProcedureRule(
        "eyelid_surgery",
        (
            r"\bdouble[- ]eyelid(?: incision| suture| buried suture)? surgery\b",
            r"\bdouble[- ]eyelid revision\b",
            r"\bdouble[- ]eyelid suture\b",
            r"\bdouble[- ]eyelid buried sutures?\b",
            r"\bdouble[- ]eyelid\b",
            r"\beyelid surgery\b",
            r"\beyelid procedure\b",
            r"\beye procedure to address monolids? and drooping\b",
        ),
    ),
    ProcedureRule(
        "epicanthoplasty",
        (
            r"\bepicanthoplast(?:y|ies)\b",
            r"\binner corner eye incision\b",
            r"\binner eye corner\b",
        ),
    ),
    ProcedureRule(
        "lateral_lower_canthoplasty",
        (
            r"\blateral and lower canthoplasty\b",
            r"\blateral canthoplasty\b",
            r"\blower canthoplasty\b",
            r"\bcanthoplasty\b",
            r"\beye-lowering surgery\b",
            r"\blower and reshape the outer corners?\b",
            r"\bback-and-bottom eye corner revision\b",
            r"\bposterior lower blepharoplasty\b",
            r"\beye corner procedure\b",
            r"\bcorner eye procedures?\b",
        ),
    ),
    ProcedureRule(
        "ptosis_correction",
        (
            r"\bptosis correction\b",
            r"\beye-opening procedure\b",
            r"\bweak eye-opening strength\b",
            r"\bweakness that made it hard to open the eyes\b",
            r"\bstronger eyelid opening\b",
            r"\beye-area surgery to improve .*openness\b",
            r"\beye surgery to correct a sleepy-looking appearance\b",
            r"\bneed to strain to keep the eyes open\b",
            r"\beye muscle correction\b",
            r"\beye[- ]shape correction\b",
            r"\beye-area correction\b",
            r"\beye correction\b",
            r"\beyelid surgery to correct a sleepy-looking appearance\b",
        ),
    ),
    ProcedureRule(
        "lower_eyelid_surgery",
        (
            r"\blower eyelid surgery\b",
        ),
    ),
    ProcedureRule(
        "facial_contouring",
        (
            r"\bfacial contour(?:ing)? surgery\b",
            r"\bfacial contouring\b",
            r"\bjawline-contouring surgery\b",
            r"\bcontour surgery\b",
        ),
    ),
    ProcedureRule(
        "forehead_lift",
        (
            r"\bforehead lift\b",
        ),
    ),
    ProcedureRule(
        "neck_muscle_reduction",
        (
            r"\banterior neck muscle resection\b",
            r"\bneck muscle reduction\b",
            r"\bbrow muscle removal\b",
            r"\bcorrugator muscle removal\b",
        ),
    ),
    ProcedureRule(
        "facial_liposuction",
        (
            r"\bfacial liposuction\b",
        ),
    ),
    ProcedureRule(
        "thread_lift",
        (
            r"\bthread lift(?:ing)?\b",
        ),
    ),
    ProcedureRule(
        "chin_pin_removal",
        (
            r"\bchin pin removal\b",
            r"\bpin removal surgery\b",
        ),
    ),
    ProcedureRule(
        "breast_augmentation",
        (
            r"\bbreast augmentation\b",
            r"\bmotiva breast augmentation\b",
            r"\bbreast augmentation with .*implants?\b",
        ),
    ),
    ProcedureRule(
        "breast_lift",
        (
            r"\bbreast lift(?:ing)? surgery\b",
            r"\bbreast lift\b",
        ),
    ),
    ProcedureRule(
        "trapezius_reduction",
        (
            r"\bshoulder botox\b",
            r"\breducing trapezius muscle bulk\b",
            r"\btrapezius muscle bulk\b",
        ),
    ),
    ProcedureRule(
        "face_slimming_treatment",
        (
            r"\bface-slimming treatment\b",
        ),
    ),
    ProcedureRule(
        "facial_slimming_acupuncture",
        (
            r"\bfacial slimming acupuncture\b",
        ),
    ),
    ProcedureRule(
        "spot_redness_treatment",
        (
            r"\bfine facial spots and redness\b",
        ),
    ),
    ProcedureRule(
        "sunspot_dullness_treatment",
        (
            r"\bsun spots and dullness\b",
        ),
    ),
    ProcedureRule(
        "bruxism_bite_treatment",
        (
            r"\bbite misalignment\b",
            r"\bbad bite\b",
            r"\bteeth grinding\b",
        ),
    ),
    ProcedureRule(
        "face_shoulder_treatment",
        (
            r"\bsmaller face and relieve shoulder stiffness\b",
        ),
    ),
)

_COMPILED_RULES = tuple(
    (
        rule.procedure_id,
        tuple(re.compile(pattern, re.IGNORECASE) for pattern in rule.patterns),
    )
    for rule in PROCEDURE_RULES
)

_REVISION_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\brevision\b",
        r"\bthird rhinoplasty\b",
        r"\bthird operation\b",
    )
)


@dataclass(frozen=True)
class ProcedureExtraction:
    procedures: tuple[str, ...]
    primary_procedure: str | None
    revision: bool
    signature: str | None


PRIMARY_PROCEDURE_PRIORITY: tuple[str, ...] = (
    "ptosis_correction",
    "lateral_lower_canthoplasty",
    "lower_eyelid_surgery",
    "epicanthoplasty",
    "alar_reduction",
    "rhinoplasty",
    "breast_lift",
    "breast_augmentation",
    "facial_contouring",
    "forehead_lift",
    "facial_liposuction",
    "thread_lift",
    "chin_pin_removal",
    "trapezius_reduction",
    "facial_slimming_acupuncture",
    "face_slimming_treatment",
    "spot_redness_treatment",
    "sunspot_dullness_treatment",
    "bruxism_bite_treatment",
    "face_shoulder_treatment",
    "neck_muscle_reduction",
    "eyelid_surgery",
)


def extract_procedures(text: str) -> ProcedureExtraction:
    matched = {
        procedure_id
        for procedure_id, patterns in _COMPILED_RULES
        if any(pattern.search(text) for pattern in patterns)
    }
    procedures = tuple(sorted(matched))
    revision = any(pattern.search(text) for pattern in _REVISION_PATTERNS)

    signature_set = set(matched)
    eye_corner_tags = {
        "epicanthoplasty",
        "lateral_lower_canthoplasty",
        "lower_eyelid_surgery",
    }
    if signature_set & eye_corner_tags:
        signature_set.difference_update(eye_corner_tags)
        signature_set.add("eye_corner_surgery")
    if "eye_corner_surgery" in signature_set or "ptosis_correction" in signature_set:
        signature_set.discard("eyelid_surgery")

    primary_procedure = next(
        (procedure for procedure in PRIMARY_PROCEDURE_PRIORITY if procedure in matched),
        None,
    )
    signature = "|".join(sorted(signature_set)) if signature_set else None

    return ProcedureExtraction(
        procedures=procedures,
        primary_procedure=primary_procedure,
        revision=revision,
        signature=signature,
    )