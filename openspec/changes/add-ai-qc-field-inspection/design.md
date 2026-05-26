## Context

The project already contains YOLO training and inference scripts plus recent field-survey media under `E:\yolo\素材`. The current field media covers three candidate AI QC scenarios: steel/rebar material counting, rebar mechanical coupler exposed-thread checks, and concrete surface inspection. The material is enough for feasibility assessment and an assisted-inspection Demo, but it is not yet enough for a production model without additional labeled positive/negative samples.

The stakeholders need a practical first delivery for construction-site quality control. Site users will likely capture photos or short videos on phones, while quality engineers need annotated evidence, counts, suspicious/non-compliant flags, and a reviewable issue list. The first implementation must avoid over-claiming final compliance because some rules depend on project standards, capture angle, and scale calibration.

## Goals / Non-Goals

**Goals:**

- Define a first AI QC pilot covering shared field capture, steel/rebar material counting, coupler exposed-thread screening, and concrete surface screening.
- Support offline/local Demo execution before committing to H5, Android, iOS, or app-store distribution.
- Require project/location metadata and capture guidance so results can be reviewed and traced back to site context.
- Produce annotated images, structured JSON/CSV summaries, and manual-review flags.
- Keep final quality acceptance with human reviewers while the model and capture process are being validated.

**Non-Goals:**

- Do not build a production mobile app in this change.
- Do not require iOS App Store/TestFlight delivery for the first pilot.
- Do not perform BIM comparison, drawing-level conformance checks, or automatic rectification workflows.
- Do not promise millimeter-level measurement unless a scale reference or calibrated camera setup is present.
- Do not replace formal quality acceptance or supervision sign-off with AI output.

## Decisions

1. Use a scenario router plus independent analyzers.

   Rationale: the three scenarios have different visual cues, rules, and failure modes. A shared router can normalize media intake and metadata, then dispatch to focused analyzers for counting, coupler QC, or concrete surface QC. Alternative considered: train one broad detector immediately. That would be faster to demo superficially but would blur labels, thresholds, and acceptance criteria.

2. Treat capture metadata and photo guidance as part of the capability.

   Rationale: field photos without project, floor, axis, component, scenario, and capture angle cannot reliably enter a rectification workflow. The system will accept media only with enough metadata to trace results and will emit guidance when capture quality is insufficient. Alternative considered: run inference on arbitrary folders only. That is useful for experiments but not enough for site use.

3. Deliver the first version as assisted inspection.

   Rationale: current materials support detection and screening, not final compliance. Outputs will include annotated evidence, confidence, reason codes, and review status. Alternative considered: output direct pass/fail only. That would create avoidable risk when standards or calibration are missing.

4. Make coupler exposed-thread QC threshold-driven.

   Rationale: compliance depends on project rules such as allowed exposed thread count or exposed length by coupler/diameter. The analyzer will detect couplers and thread regions, then apply supplied thresholds. If no threshold or scale exists, it will flag "needs review" instead of declaring non-compliance. Alternative considered: hard-code one visible-thread rule. That would be brittle across projects and coupler types.

5. Limit first material counting to endpoint-visible bundles.

   Rationale: endpoint photos make each bar visually separable and produce a credible count. Side-view piles, stacked bundles, straps, gloves, and tarps introduce occlusion and must be treated as estimates or review-needed. Alternative considered: count all pile images equally. That would reduce trust in the first Demo.

6. Start concrete surface QC with visible-defect screening.

   Rationale: the current photos contain mostly normal surfaces, repair marks, color differences, seams, and water/flow marks; obvious honeycombing, pitting, exposed rebar, holes, and cracks need more samples. The first concrete analyzer will identify suspected defect/anomaly regions and defer final grading and precise area/width measurement unless calibrated. Alternative considered: claim full concrete quality acceptance. The available data does not support that.

7. Store pilot data and outputs in scenario-specific folders.

   Rationale: separate folders for raw media, selected samples, labels, predictions, and reports will keep steel counting, coupler QC, and concrete QC from contaminating each other. A practical layout is `datasets/field_qc/<scenario>/raw`, `labels`, `predictions`, and `reports`.

## Risks / Trade-offs

- Insufficient labeled samples -> Start with feasibility/Demo outputs and collect at least dozens of positive/negative samples per scenario before claiming stable model performance.
- Inconsistent capture angles -> Add capture guidance and reject/flag low-quality media rather than returning confident results.
- Missing scale reference -> Limit output to counts and suspicious regions; require ruler, known diameter, marker, or camera calibration for length/area measurements.
- Ambiguous compliance standards -> Put thresholds in configuration and require business confirmation before pass/fail flags.
- Occlusion in material piles -> Count endpoint-visible bars and mark side-view or occluded bundles as manual review.
- Concrete surface false positives from repair marks and stains -> Use a defect taxonomy with "surface anomaly" and "needs review" classes before enforcing defect severity.

## Migration Plan

1. Create scenario-specific sample inventories from the current field media.
2. Define label taxonomies and capture-quality rules for the four capabilities.
3. Implement offline analyzers that read local media and write annotated images plus JSON/CSV reports.
4. Run the analyzers on the current field media and review outputs with quality stakeholders.
5. Collect additional labeled samples where performance or taxonomy is weak.
6. Only after the POC is accepted, decide whether the upload surface should be H5, Android APK, enterprise distribution, or iOS.

Rollback is simple during the POC: remove the new field-QC datasets, analyzer scripts, and reports. Existing PPE training and inference flows are not modified by this proposal.

## Open Questions

- What exact exposed-thread rule applies by coupler type and steel diameter: visible thread count, exposed length, or both?
- What is the counting unit for material inventory: root/bar, bundle, batch, or receipt-line quantity?
- Which concrete defects are in scope for first acceptance: honeycombing, pitting, exposed rebar, holes, cracks, leakage marks, repair patches, color difference, formwork seams, or错台?
- What metadata fields are mandatory for site traceability: project, zone, building, floor, axis, component ID, inspection batch, photographer, timestamp?
- Will field teams agree to a capture rule requiring endpoint photos, near/far photos, and scale references where measurement is needed?
