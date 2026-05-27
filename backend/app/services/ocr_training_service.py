import os
import json
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class OCRTrainingService:
    """Persist sidewall extraction results for later OCR model training.

    The service saves the original sidewall image and the structured metadata
    extracted by Gemini into a designated training data directory.  Downstream
    training pipelines can consume these files to fine‑tune or retrain the OCR
    model.
    """

    def __init__(self, base_dir: str = None):
        # Default to project-wide dataset OCR training folder
        self.base_dir = Path(base_dir or os.getenv("OCR_TRAINING_DIR", "dataset/ocr_training_examples"))
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("OCRTrainingService initialized at %s", self.base_dir)

    def _timestamp(self) -> str:
        return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    def _save_image(self, image_bytes: bytes, suffix: str) -> Path:
        filename = f"sidewall_{self._timestamp()}{suffix}"
        path = self.base_dir / filename
        with open(path, "wb") as f:
            f.write(image_bytes)
        logger.info("Saved sidewall image for OCR training: %s", path)
        return path

    def _save_metadata(self, metadata: dict, image_path: Path) -> Path:
        meta_path = image_path.with_suffix(".json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        logger.info("Saved OCR training metadata: %s", meta_path)
        return meta_path

    def add_example(self, image_bytes: bytes, extracted_details: dict) -> None:
        """Store a sidewall image and its extracted details.

        Args:
            image_bytes: Raw bytes of the sidewall image received from the API.
            extracted_details: Dict returned by :class:`SidewallService` containing
                fields such as ``brand``, ``tire_size``, ``dot_code`` etc.
        """
        try:
            # Preserve original MIME type information if available
            mime = extracted_details.get("mime_type", "image/jpeg")
            suffix = ".jpg" if "jpeg" in mime else ".png"
            img_path = self._save_image(image_bytes, suffix)
            self._save_metadata(extracted_details, img_path)
        except Exception as e:
            logger.error("Failed to store OCR training example: %s", e)
