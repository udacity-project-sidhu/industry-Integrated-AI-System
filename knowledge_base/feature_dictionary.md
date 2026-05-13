# UCI (University of California, Irvine) Heart Disease — Feature Dictionary

Clinical meaning of each feature used by the risk-scoring models. This document is part of the knowledge base retrieved by the agent at explanation time, so values cited in patient-facing summaries can be traced back here.

## Demographics

- **age** — Age in years. Cardiovascular disease prevalence rises with age; risk roughly doubles every decade after 55 (American Heart Association, 2022).
- **sex** — Biological sex (1 = male, 0 = female). Male sex is an independent risk factor for premature coronary disease; female risk converges after menopause.

## Symptom history

- **cp — chest pain type**
  - 1 = typical angina (substernal, exertion-related, relieved by rest or nitroglycerin)
  - 2 = atypical angina
  - 3 = non-anginal pain
  - 4 = asymptomatic
  Typical angina has the strongest association with obstructive coronary disease; asymptomatic presentations in the dataset typically come from screening referrals.
- **exang — exercise-induced angina** (1 = yes, 0 = no). Reproduces ischemia under stress; positive findings raise pretest probability of disease.

## Vital signs and labs

- **trestbps — resting blood pressure** (mm Hg — millimeters of mercury, measured on hospital admission). Chronic hypertension (>140/90) damages endothelium and accelerates atherosclerosis.
- **chol — serum cholesterol** (mg/dl — milligrams per deciliter). Total cholesterol; LDL (low-density lipoprotein) fraction is more directly atherogenic but is not separately recorded in this dataset.
- **fbs — fasting blood sugar > 120 mg/dl** (1 = true). A surrogate for diabetes/pre-diabetes, which roughly doubles cardiovascular risk.

## Resting ECG (electrocardiogram)

- **restecg — resting electrocardiographic results**
  - 0 = normal
  - 1 = ST-T wave abnormality (T-wave inversions or ST elevation/depression > 0.05 mV)
  - 2 = probable or definite left-ventricular hypertrophy (LVH) by Estes' criteria
  LVH and persistent ST-T changes reflect chronic hemodynamic stress on the heart.

## Stress test

- **thalach — maximum heart rate achieved during exercise** (bpm — beats per minute). Lower peak heart rate (especially below 85% of age-predicted maximum) suggests reduced functional capacity or chronotropic incompetence.
- **oldpeak — ST depression induced by exercise relative to rest** (mm). Larger ST depression at peak exercise is a classic marker of inducible ischemia.
- **slope — slope of the peak exercise ST segment**
  - 1 = upsloping (relatively benign)
  - 2 = flat (suggestive of ischemia)
  - 3 = downsloping (more strongly suggestive of ischemia)

## Imaging / advanced workup

- **ca — number of major vessels (0–3) colored by fluoroscopy** during cardiac catheterisation. Higher counts indicate more extensive coronary perfusion.
- **thal — thalassemia / myocardial perfusion result**
  - 3 = normal
  - 6 = fixed defect (scar from prior infarction)
  - 7 = reversible defect (inducible ischemia)
  Reversible defects most strongly predict the binary disease label in this dataset.

## Target

- **num** — Original severity target (0–4); 0 = no disease, 1–4 = increasing severity.
- **target** — Binary outcome derived from `num` for this project (1 = disease present).

## Caveats

- Several features (`ca`, `thal`, `oldpeak`, `slope`) require invasive or stress testing and are not available at intake. A production triage system would split features into "available at intake" vs "available after workup".
- The dataset is small (~300 records) and skews male and older; per-slice metrics should always accompany headline metrics.
