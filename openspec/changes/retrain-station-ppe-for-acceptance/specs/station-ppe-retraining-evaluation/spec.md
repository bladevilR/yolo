## ADDED Requirements

### Requirement: Reproducible training run
Every retraining run SHALL record the exact dataset, model, hyperparameters, code entrypoint, output directory, and baseline comparison target.

#### Scenario: Start retraining run
- **WHEN** a PPE retraining script is executed
- **THEN** the run SHALL write or preserve the dataset path, training parameters, model weights, seed, image size, epochs, device, and output run name

#### Scenario: Compare against baseline
- **WHEN** a new candidate model is evaluated
- **THEN** the report SHALL compare it against the frozen V2 baseline model and document whether the candidate improves, regresses, or remains inconclusive

### Requirement: Controlled retraining experiments
The retraining workflow SHALL support controlled experiments that vary one major training choice at a time.

#### Scenario: Compare image size
- **WHEN** image size is evaluated for small PPE targets
- **THEN** the workflow SHALL compare runs such as 640 and 960 input size using the same reviewed dataset and record the metric and latency trade-off

#### Scenario: Compare model scale
- **WHEN** a larger detector such as YOLOv8s is evaluated
- **THEN** the workflow SHALL keep the dataset and split fixed so accuracy changes can be attributed to model scale

### Requirement: Detector metric report
Every candidate model SHALL report detector metrics by split and class.

#### Scenario: Report normal validation metrics
- **WHEN** training completes
- **THEN** the report SHALL include precision, recall, mAP50, mAP50-95, confusion matrix, and per-class results for `person`, `helmet`, and `vest` on normal validation and test splits

#### Scenario: Report stress metrics
- **WHEN** stress samples are evaluated
- **THEN** the report SHALL separately include false-person rate, duplicate-person rate, missed-worker examples, and PPE confusion examples for stress cases

### Requirement: Event-level evaluation
The retraining workflow SHALL evaluate the strict demo event pipeline in addition to detector boxes.

#### Scenario: Run strict demo evaluation
- **WHEN** a candidate model is selected for demo verification
- **THEN** the strict demo workflow SHALL generate annotated images, event CSV, rejected candidates, and manual review queue summaries

#### Scenario: Review violation events
- **WHEN** suspected no-helmet or no-vest events are generated
- **THEN** the evaluation report SHALL distinguish auto-demo events, needs-review events, and rejected candidates

### Requirement: Acceptance decision report
Every retraining cycle SHALL produce a decision report that separates technical demo readiness from business acceptance.

#### Scenario: Candidate passes technical demo only
- **WHEN** the detector improves presentation cleanliness but still has unreviewed labels, unstable vest behavior, or high false event risk
- **THEN** the report SHALL mark it as technical-demo-ready only and SHALL NOT mark it as business-accepted

#### Scenario: Candidate can be proposed for business acceptance
- **WHEN** the model is trained on human-reviewed data and passes normal metrics, stress metrics, and event-level review thresholds agreed for the milestone
- **THEN** the report MAY recommend business acceptance review while preserving metric evidence and residual risks
