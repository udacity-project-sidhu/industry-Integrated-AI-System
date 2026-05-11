# Cardiovascular Risk Factors — Reference Notes

Concise, citation-bearing notes used by the agent to ground patient explanations. These are general clinical concepts, not patient-specific advice.

## Major modifiable risk factors

- **Hypertension.** Persistently elevated systolic blood pressure (>140 mm Hg) is the single largest contributor to global cardiovascular mortality. Lowering systolic BP by 10 mm Hg reduces major cardiovascular events by roughly 20% (Ettehad et al., 2016, *Lancet*).
- **Dyslipidemia.** Elevated LDL cholesterol drives atherogenesis. Statin therapy reduces LDL by 30–50% and lowers major vascular events by approximately 22% per 1 mmol/L LDL reduction (CTT Collaboration, 2010, *Lancet*).
- **Diabetes / hyperglycemia.** Diabetes roughly doubles cardiovascular risk independently of other factors (Sarwar et al., 2010, *Lancet*). Fasting blood sugar > 120 mg/dl is a screening flag.
- **Smoking.** Doubles the risk of coronary events; risk declines toward baseline within 5–10 years of cessation. Not recorded in the UCI Heart Disease dataset — an important data gap.
- **Sedentary behaviour.** Lower exercise capacity (peak `thalach` below 85% of age-predicted maximum) is independently associated with cardiovascular mortality (Ross et al., 2016, *Circulation*).

## Non-modifiable risk factors

- **Age.** Risk approximately doubles each decade after 55.
- **Sex.** Male sex is an independent risk factor for premature coronary disease; female risk rises sharply after menopause.
- **Family history.** Premature coronary disease in a first-degree relative roughly doubles risk. Not recorded in this dataset.

## Diagnostic findings on this dataset

- **Typical angina (`cp` = 1).** Highest pretest probability of obstructive coronary disease among the four chest-pain categories.
- **Exercise-induced angina (`exang` = 1).** Strong correlate of inducible ischemia.
- **ST depression on exercise (`oldpeak`).** ≥ 1 mm horizontal/downsloping depression at peak exercise is a classical positive stress test.
- **Reversible perfusion defect (`thal` = 7).** Most directly indicative of inducible ischemia in this dataset.
- **Multi-vessel disease (`ca` ≥ 1).** Each additional diseased vessel substantially raises the probability of the disease label.

## What this system does *not* know

- Family history, smoking status, BMI, HbA1c, LDL/HDL fractions, medication history.
- Symptom acuity (chest pain at rest? new-onset? worsening?).
- Imaging beyond fluoroscopy vessel count.
- Patient preferences, social context, access to follow-up care.

Any explanation produced by this system must therefore be treated as *suggestive*, not diagnostic. The clinician is the locus of accountability for treatment decisions.

## References

- American Heart Association (2022). *Heart Disease and Stroke Statistics — 2022 Update*. *Circulation*, 145(8), e153–e639.
- Cholesterol Treatment Trialists' (CTT) Collaboration (2010). Efficacy and safety of more intensive lowering of LDL cholesterol. *Lancet*, 376(9753), 1670–1681.
- Ettehad, D. et al. (2016). Blood pressure lowering for prevention of cardiovascular disease and death. *Lancet*, 387(10022), 957–967.
- Ross, R. et al. (2016). Importance of assessing cardiorespiratory fitness in clinical practice. *Circulation*, 134(24), e653–e699.
- Sarwar, N. et al. (2010). Diabetes mellitus, fasting blood glucose concentration, and risk of vascular disease. *Lancet*, 375(9733), 2215–2222.
