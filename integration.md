# Integration

Place autoexam_ml beside the project's backend package. Load artifacts/model.json at process startup using load_model. Import evaluate_descriptive from autoexam_ml.integration and call it for descriptive answers. Preserve the existing grades until a faculty member approves using model scores. The adapter returns confidence as None because the model does not estimate calibrated uncertainty. When integrating with an existing grade database, preserve its confidence schema and use the review flag for routing.
