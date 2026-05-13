# Triage Workflow — Clinician-Facing Summary Template

Guidance retrieved by the agent at explanation time. Defines the structure of a well-formed patient explanation and the safety language the system must include.

## Structure of an acceptable explanation

A clinician-facing summary should contain, in order:

1. **One-line risk tier** with the ensemble probability and the threshold used (e.g. "Moderate risk: ensemble probability 0.42, tiered against low<0.30 / high≥0.70").
2. **Model agreement** — note whether the ML (Machine Learning) and DL (Deep Learning) scorers agree (within 0.20). If they disagree, state that the explanation is low-confidence and the case should be escalated.
3. **Top contributing factors** — three to five features from the patient record that align with documented cardiovascular risk factors (see `risk_factors.md`). Each factor must cite the feature dictionary.
4. **What this system does not know** — explicit list of variables absent from the dataset (smoking status, family history, medications, BMI (Body Mass Index), HbA1c (glycated hemoglobin), LDL (low-density lipoprotein) / HDL (high-density lipoprotein) fractions, symptom acuity).
5. **Disclaimer** — "Educational artifact only. Not for clinical use. The clinician is the locus of accountability."

## Refusal cases

The system must refuse to produce an explanation when:

- The retrieval step returns no chunks above a usable similarity threshold.
- The patient features fail validation (out-of-range values, missing required fields).
- The model-agreement gap is large *and* the user has explicitly requested a definitive tier.

In a refusal, the system returns `INSUFFICIENT EVIDENCE` plus a one-line reason. It does not fall back to its priors.

## Banned content

- No prescription of medications, dosages, or specific treatments.
- No definitive diagnosis ("the patient has coronary artery disease").
- No prognostic claims ("the patient will have a heart attack in X years").
- No statements about non-cardiovascular conditions.

## Style

- Neutral, analytical, concise (under 250 words).
- No marketing language, no hedged certainty ("clearly", "obviously").
- Cite every quoted feature value or risk factor.
