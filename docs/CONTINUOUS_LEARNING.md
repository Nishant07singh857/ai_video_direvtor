# Continuous Learning & Error-to-Training System

## The Continuous Learning Loop
The AI must continuously learn from its own mistakes, user corrections, rejected/accepted decisions, critic findings, and technical failures.

"Learning" must NOT mean blindly changing the production model after every error.
Every learning signal must pass through:
`ERROR → CAPTURE → CLASSIFY → ANALYZE → EXTRACT LEARNING SIGNAL → STORE → VALIDATE → DATASET → EVALUATE → TRAIN/FINE-TUNE → BENCHMARK → SHADOW TEST → CONTROLLED DEPLOYMENT`

## Error Taxonomy
1. **EDITORIAL_ERRORS**: wrong shot selection, wrong story order, wrong pacing, bad transition, continuity problem, etc.
2. **TECHNICAL_ERRORS**: invalid timeline operation, render failure, corrupted asset, missing media, etc.
3. **AI_ERRORS**: hallucinated interpretation, unsupported claim, incorrect scene classification, etc.
4. **UX_ERRORS**: user repeatedly reverses an action or manually corrects the same operation.

## Error Capture System
Every significant failure becomes an event in the `ai_error_events` table. 
Severities: `INFO`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.

## Human Correction Capture
The system must recognize when a human corrects the AI (e.g., AI selects Shot A, user deletes and selects Shot B). These corrections become structured learning signals (pairwise preference data).

## Accept / Reject / Modify Signals
Every AI operation can receive `ACCEPTED`, `REJECTED`, `MODIFIED`, or `PARTIALLY_ACCEPTED`.
Store the exact correction as preference data (e.g., Preference: B > A), not just negative labels.

## AI Critic Learning
AI Critic identifies issues (e.g., PACING_TOO_SLOW). Human can `CONFIRM`, `REJECT`, or `MODIFY`. This becomes evaluation/training data.

## Project & Editor Level Learning
Each project and editor can have their own editorial memory (e.g., preferred pacing, transition style). Project memory must NOT automatically become global model training data.

## Global Learning Dataset
Only high-quality learning signals enter the global training dataset via a pipeline:
`RAW EVENTS → DEDUPLICATION → QUALITY FILTER → PRIVACY FILTER → LABEL NORMALIZATION → CONTEXT VALIDATION → HUMAN / AUTOMATED QUALITY CHECK → TRAINING DATASET`

## Training Dataset Types
Separate datasets for: Shot Ranking, Shot Duration, Story Ordering, B-roll, Transition, Pacing, Continuity, AI Critic, Preference, Natural Language Edit.

## Model Specialization & Registry
Use specialized models (Vision, Embedding, Ranking, Preference, Critic, Speech) rather than forcing everything into one LLM.
Models are tracked in the `model_registry` table.
Statuses: `TRAINING`, `EVALUATING`, `SHADOW`, `PRODUCTION`, `RETIRED`, `FAILED`.

## Online Learning Safety & Governance
Do NOT directly modify production model weights from live user actions.
`USER ERROR → LEARNING EVENT → DATASET → TRAINING → EVALUATION → SHADOW MODEL → APPROVAL → DEPLOY`
Automated scheduled training with fixed benchmark evaluations and regression testing.
Must support model rollback. Priority learning based on severity/frequency.
