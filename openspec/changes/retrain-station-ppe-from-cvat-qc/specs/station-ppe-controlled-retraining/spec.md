## ADDED Requirements

### Requirement: Training Runs Are Reproducible
The system SHALL run station PPE retraining from a frozen dataset with recorded model, data path, image size, epochs, batch size, seed, device, dependency versions, and output directory.

#### Scenario: Training manifest written
- **WHEN** a retraining run starts
- **THEN** it writes a run manifest containing dataset snapshot ID, split manifests, class map, training parameters, code revision when available, and output paths

#### Scenario: Run artifacts are preserved
- **WHEN** training completes
- **THEN** weights, `args.yaml`, `results.csv`, confusion matrices, label plots, validation predictions, and run manifest remain in the run output directory

### Requirement: Pilot And Candidate Runs Are Distinguished
The system SHALL distinguish quick pilot runs from candidate runs that can be considered for deployment or acceptance.

#### Scenario: Pilot run label
- **WHEN** a model is trained before all current CVAT task images are reviewed or skipped
- **THEN** the run is labeled as pilot-only and cannot be reported as acceptance-ready

#### Scenario: Candidate run gate
- **WHEN** a model is trained for candidate selection
- **THEN** the dataset gate has passed, split manifests are frozen, and the candidate run references the approved dataset report

### Requirement: Controlled Experiments Compare Like With Like
The system SHALL compare model and image-size experiments using the same frozen dataset and split manifests.

#### Scenario: Image-size experiment
- **WHEN** 640 and 960 image-size experiments are run
- **THEN** both runs use the same dataset snapshot, split manifests, seed policy, and evaluation scripts

#### Scenario: Model-scale experiment
- **WHEN** YOLO model scale is varied
- **THEN** the report separates accuracy improvement from latency or deployment-cost impact

### Requirement: Baseline Comparison Is Required
The system SHALL compare each candidate model against the existing V2 demo baseline.

#### Scenario: Baseline metrics included
- **WHEN** an evaluation report is generated
- **THEN** it includes the V2 baseline path, V2 detector metrics if available, V2 strict demo/event counts, and the candidate delta

### Requirement: Detector Evaluation Covers Normal And Stress Sets
The system SHALL evaluate candidate models on normal validation/test splits and separately on stress samples.

#### Scenario: Normal detector metrics
- **WHEN** validation or test evaluation runs
- **THEN** the report includes precision, recall, mAP50, mAP50-95, per-class metrics, and confusion matrices

#### Scenario: Stress detector metrics
- **WHEN** stress evaluation runs
- **THEN** the report includes false-person cases, duplicate-person cases, missed-worker cases, PPE confusion cases, and hard-negative failure examples

### Requirement: Event-Level Demo Evaluation Is Required
The system SHALL run the strict demo/event pipeline for the leading candidate before any readiness claim.

#### Scenario: Event artifacts generated
- **WHEN** strict demo evaluation runs
- **THEN** it writes annotated outputs, event CSV, rejected candidate CSV, manual review queue summary, and event-level counts

#### Scenario: PPE event quality reported
- **WHEN** demo events are manually reviewed
- **THEN** the report includes suspected no-helmet precision and recall, suspected no-vest precision and recall where labels support it, false event count, duplicate event count, and manual-review queue volume

### Requirement: Candidate Decision Report Is Produced
The system SHALL produce a final decision report for each leading run.

#### Scenario: Readiness status assigned
- **WHEN** candidate evaluation finishes
- **THEN** the decision report labels the result as `demo-ready`, `pilot-ready`, `business-acceptance-ready`, or `rejected`

#### Scenario: Rejection reasons recorded
- **WHEN** a run is rejected
- **THEN** the report records the blocking reason so future training does not repeat the same failure mode
