"""
Backward-compatible shim.

The canonical module has moved to ``continuous_learning.sample_storage``.
This file re-exports every public name so existing ``from app.services
.continuous_learning_service import ...`` statements keep working.
"""

from continuous_learning.sample_storage import (  # noqa: F401
    CONTINUOUS_ROOT,
    CORRECTIONS_DIR,
    FRONT_VIEW_DIR,
    LABELS_CSV,
    LABEL_COLUMNS,
    PROJECT_ROOT,
    PREDICTIONS_DIR,
    save_analysis_sample,
    save_feedback_correction,
)
