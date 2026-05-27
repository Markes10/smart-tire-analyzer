"""
Dataset loader that builds tf.data pipelines for training and validation.
Handles CSV label loading, image loading, preprocessing, and batching.
"""

from __future__ import annotations

import logging
import random
from collections.abc import Generator, Sequence
from pathlib import Path
from typing import Any, Protocol, TypeAlias, TypedDict, cast, runtime_checkable

import numpy as np
import numpy.typing as npt
import pandas as pd
import tensorflow as tf

logger = logging.getLogger(__name__)
try:
    from dataset.class_schemas import get_classes, mm_to_tread_depth_class  # type: ignore
except Exception:
    # schemas not available — provide safe fallbacks
    def get_classes(name: str):  # type: ignore
        return []

    def mm_to_tread_depth_class(mm: float):  # type: ignore
        return None

TREAD_MAX_MM = 12.0
HEALTH_MAX = 10.0
MAX_REMAINING_KM = 80000.0
IMAGE_SIZE = (224, 224)
IMAGE_CHANNELS = 4
TREAD_SEQUENCE_SHAPE = (4, 7)
CONTEXT_SIZE = 32
NUM_WEAR_CLASSES = 6
TREAD_COLUMNS = ("tread_1", "tread_2", "tread_3", "tread_4")

# If schemas are available, prefer the canonical wear pattern count.
try:
    _wc = get_classes("wear_pattern")
    if _wc:
        NUM_WEAR_CLASSES = len(_wc)
except Exception:
    pass

Float32Array: TypeAlias = npt.NDArray[np.float32]
Int32Array: TypeAlias = npt.NDArray[np.int32]
DatasetType: TypeAlias = Any
DataFrameType: TypeAlias = Any
TensorDict: TypeAlias = dict[str, Any]
LabelFrames: TypeAlias = tuple[DataFrameType | None, DataFrameType | None, DataFrameType | None]


class InputBatch(TypedDict):
    image: Float32Array
    tread_sequence: Float32Array
    context: Float32Array


class TargetBatch(TypedDict):
    tread_depths: Float32Array
    health_score: Float32Array
    remaining_life: Float32Array
    wear_pattern: np.int32


@runtime_checkable
class SupportsNumpy(Protocol):
    def numpy(self) -> object: ...


def _as_float32_array(value: npt.ArrayLike) -> Float32Array:
    """Convert array-like data to a float32 NumPy array."""
    return np.asarray(value, dtype=np.float32)


def _as_int32_array(value: npt.ArrayLike) -> Int32Array:
    """Convert array-like data to an int32 NumPy array."""
    return np.asarray(value, dtype=np.int32)


def _unwrap_scalar_tensorlike(value: object) -> object:
    """Resolve TensorFlow and NumPy scalar wrappers into plain Python objects."""
    candidate: object = value.numpy() if isinstance(value, SupportsNumpy) else value
    if isinstance(candidate, np.ndarray):
        candidate = cast(object, candidate.item())
    if isinstance(candidate, np.generic):
        return cast(object, candidate.item())
    return candidate


def _decode_string_value(value: object) -> str:
    """Decode TensorFlow or NumPy string-like values to Python strings."""
    candidate = _unwrap_scalar_tensorlike(value)
    if isinstance(candidate, np.bytes_):
        return candidate.decode("utf-8")
    if isinstance(candidate, bytes):
        return candidate.decode("utf-8")
    return str(candidate)


def _float_from_tensorlike(value: object) -> np.float32:
    """Extract a scalar float32 from a TensorFlow or NumPy value."""
    candidate = _unwrap_scalar_tensorlike(value)
    if isinstance(candidate, (bool, int, float)):
        return np.float32(float(candidate))
    if isinstance(candidate, (str, bytes, np.bytes_)):
        return np.float32(float(candidate))
    raise TypeError(f"Expected float-like value, received {type(candidate).__name__}")


def _int_from_tensorlike(value: object) -> np.int32:
    """Extract a scalar int32 from a TensorFlow or NumPy value."""
    candidate = _unwrap_scalar_tensorlike(value)
    if isinstance(candidate, (bool, int, float)):
        return np.int32(int(candidate))
    if isinstance(candidate, (str, bytes, np.bytes_)):
        return np.int32(int(candidate))
    raise TypeError(f"Expected int-like value, received {type(candidate).__name__}")


def _float_array_from_tensorlike(value: object) -> Float32Array:
    """Extract a float32 NumPy array from a TensorFlow or NumPy value."""
    candidate: Any = value.numpy() if isinstance(value, SupportsNumpy) else value
    return _as_float32_array(candidate)


def _read_csv(path: Path) -> DataFrameType:
    """Read a CSV file through a narrow pandas Any boundary."""
    pandas_module: Any = pd
    return pandas_module.read_csv(path)


def _dataframe_to_string_list(frame: DataFrameType, column: str) -> list[str]:
    """Extract a string column from a pandas DataFrame."""
    frame_any: Any = frame
    raw_values = frame_any[column].astype(str).tolist()
    return [str(value) for value in raw_values]


def _dataframe_columns_to_float32(frame: DataFrameType, columns: Sequence[str]) -> Float32Array:
    """Extract a matrix of float32 values from pandas."""
    frame_any: Any = frame
    raw_values = frame_any[list(columns)].to_numpy(dtype=np.float32)
    return _as_float32_array(raw_values)


def _dataframe_column_to_float32(frame: DataFrameType, column: str) -> Float32Array:
    """Extract a float32 vector from pandas."""
    frame_any: Any = frame
    raw_values = frame_any[column].to_numpy(dtype=np.float32)
    return _as_float32_array(raw_values)


def _dataframe_column_to_int32(frame: DataFrameType, column: str) -> Int32Array:
    """Extract an int32 vector from pandas."""
    frame_any: Any = frame
    raw_values = frame_any[column].to_numpy(dtype=np.int32)
    return _as_int32_array(raw_values)


class SmartTireDataset:
    """
    Dataset pipeline for Smart Tire training.

    Loads from (new layout):
    - dataset/raw/tread_images/{safe,moderate,replace}/  : JPEG/PNG tire images
    - dataset/processed/labels.csv                       : merged labels (T1-T4, wear, health)
    - dataset/splits/{train,validation,test}/labels.csv  : per-split CSV files

    Output per sample:
    - inputs: {'image': (224, 224, 4), 'tread_sequence': (4, 7), 'context': (32,)}
    - targets: {'tread_depths': (4,), 'health_score': (1,), 'remaining_life': (1,), 'wear_pattern': ()}
    """

    def __init__(
        self,
        split_dir: str,
        images_dir: str = "dataset/raw/tread_images",
        training: bool = True,
        augment: bool = True,
    ) -> None:
        self.split_dir = Path(split_dir)
        self.images_dir = Path(images_dir)
        self.training = training
        self.augment = augment and training

    def build(
        self,
        batch_size: int = 16,
        shuffle: bool = True,
        prefetch: Any = tf.data.AUTOTUNE,
    ) -> DatasetType:
        """
        Build and return a tf.data.Dataset for this split.

        Returns:
            Dataset yielding `(inputs_dict, targets_dict)` pairs.
        """
        tf_module: Any = tf
        tread_df, wear_df, health_df = self._load_labels()
        if tread_df is None or len(tread_df) == 0:
            logger.warning("No labels found - returning synthetic dataset")
            return self._synthetic_dataset(batch_size)

        merged = self._merge_labels(tread_df, wear_df, health_df)
        logger.info("Dataset split: %s, samples=%d", self.split_dir.name, len(merged))

        image_ids = _dataframe_to_string_list(merged, "image_id")
        tread_targets = _dataframe_columns_to_float32(merged, TREAD_COLUMNS) / np.float32(
            TREAD_MAX_MM
        )
        health_targets = _dataframe_column_to_float32(merged, "health_score") / np.float32(
            HEALTH_MAX
        )
        life_targets = _dataframe_column_to_float32(
            merged, "remaining_life_km"
        ) / np.float32(MAX_REMAINING_KM)
        wear_targets = _dataframe_column_to_int32(merged, "class_id")

        slice_data: TensorDict = {
            "image_id": image_ids,
            "tread_targets": tread_targets,
            "health_target": health_targets,
            "life_target": life_targets,
            "wear_target": wear_targets,
        }

        dataset: DatasetType = tf_module.data.Dataset.from_tensor_slices(slice_data)
        if shuffle:
            dataset = dataset.shuffle(buffer_size=len(merged), reshuffle_each_iteration=True)

        dataset = dataset.map(
            self._load_and_preprocess,
            num_parallel_calls=tf_module.data.AUTOTUNE,
        )
        dataset = dataset.batch(batch_size, drop_remainder=True)
        dataset = dataset.prefetch(prefetch)
        return dataset

    def _load_labels(self) -> LabelFrames:
        """Load label CSV files from split dir or processed dir."""
        labels_dir = self.split_dir
        tread_csv = labels_dir / "labels.csv"
        tread_df: DataFrameType | None = None
        wear_df: DataFrameType | None = None
        health_df: DataFrameType | None = None

        # Primary: per-split labels.csv (produced by split_dataset.py)
        if tread_csv.exists():
            split_df = _read_csv(tread_csv)
            return split_df, split_df, split_df

        # Fallback: unified processed files
        processed_dir = Path("dataset/processed")
        cleaned_path = processed_dir / "cleaned_dataset.csv"
        if not cleaned_path.exists():
            cleaned_path = processed_dir / "labels.csv"
        if cleaned_path.exists():
            tread_df = _read_csv(cleaned_path)
            return tread_df, tread_df, tread_df

        return tread_df, wear_df, health_df

    def _merge_labels(
        self,
        tread_df: DataFrameType,
        wear_df: DataFrameType | None,
        health_df: DataFrameType | None,
    ) -> DataFrameType:
        """Merge all label DataFrames on image_id."""
        df: Any = tread_df.copy()
        wear_df_any: Any = wear_df
        health_df_any: Any = health_df

        if wear_df_any is not None:
            if "image_id" in wear_df_any.columns:
                # Merge whichever wear columns are present (class_id and/or wear_pattern)
                merge_cols = [c for c in ("image_id", "class_id", "wear_pattern") if c in wear_df_any.columns]
                df = df.merge(wear_df_any[merge_cols], on="image_id", how="left")

        if health_df_any is not None and "health_score" not in df.columns:
            if "image_id" in health_df_any.columns:
                df = df.merge(
                    health_df_any[["image_id", "health_score", "remaining_life_km"]],
                    on="image_id",
                    how="left",
                )

        for column in TREAD_COLUMNS:
            if column in df.columns:
                df[column] = df[column].fillna(5.0)

        # If wear patterns are present as strings, try mapping them to numeric class ids
        if "wear_pattern" in df.columns:
            try:
                wear_classes = get_classes("wear_pattern")
                if wear_classes:
                    class_map = {name: idx for idx, name in enumerate(wear_classes)}
                    mapped = df["wear_pattern"].map(class_map)
                    if "class_id" in df.columns:
                        df["class_id"] = df["class_id"].fillna(mapped).fillna(int(NUM_WEAR_CLASSES // 2)).astype(int)
                    else:
                        df["class_id"] = mapped.fillna(int(NUM_WEAR_CLASSES // 2)).astype(int)
                else:
                    if "class_id" not in df.columns:
                        df["class_id"] = int(NUM_WEAR_CLASSES // 2)
            except Exception:
                if "class_id" not in df.columns:
                    df["class_id"] = int(NUM_WEAR_CLASSES // 2)
        else:
            if "class_id" not in df.columns:
                df["class_id"] = int(NUM_WEAR_CLASSES // 2)

        if "health_score" not in df.columns:
            avg_tread = df[list(TREAD_COLUMNS)].mean(axis=1)
            df["health_score"] = (avg_tread / TREAD_MAX_MM * HEALTH_MAX).clip(0, HEALTH_MAX)

        if "remaining_life_km" not in df.columns:
            avg_tread = df[list(TREAD_COLUMNS)].mean(axis=1)
            df["remaining_life_km"] = (
                (avg_tread - 1.6) / (TREAD_MAX_MM - 1.6) * MAX_REMAINING_KM
            ).clip(0)

        # Optionally add a tread depth class column using schema thresholds
        if "tread_depth_class" not in df.columns:
            try:
                if callable(mm_to_tread_depth_class):
                    df["tread_depth_class"] = (
                        df[list(TREAD_COLUMNS)].mean(axis=1).apply(lambda x: mm_to_tread_depth_class(float(x)))
                    )
            except Exception:
                # non-fatal: continue without class column
                pass

        return df.dropna(subset=["image_id"]).reset_index(drop=True)

    def _load_and_preprocess(self, record: TensorDict) -> tuple[TensorDict, TensorDict]:
        """Wrap Python preprocessing in tf.py_function for tf.data compatibility."""
        tf_module: Any = tf
        (
            image,
            tread_sequence,
            context,
            tread_depths,
            health_score,
            remaining_life,
            wear_pattern,
        ) = tf_module.py_function(
            func=self._load_and_preprocess_py,
            inp=[
                record["image_id"],
                record["tread_targets"],
                record["health_target"],
                record["life_target"],
                record["wear_target"],
            ],
            Tout=[
                tf.float32,
                tf.float32,
                tf.float32,
                tf.float32,
                tf.float32,
                tf.float32,
                tf.int32,
            ],
        )

        image.set_shape((IMAGE_SIZE[0], IMAGE_SIZE[1], IMAGE_CHANNELS))
        tread_sequence.set_shape(TREAD_SEQUENCE_SHAPE)
        context.set_shape((CONTEXT_SIZE,))
        tread_depths.set_shape((len(TREAD_COLUMNS),))
        health_score.set_shape((1,))
        remaining_life.set_shape((1,))
        wear_pattern.set_shape(())

        inputs: TensorDict = {
            "image": image,
            "tread_sequence": tread_sequence,
            "context": context,
        }
        targets: TensorDict = {
            "tread_depths": tread_depths,
            "health_score": health_score,
            "remaining_life": remaining_life,
            "wear_pattern": wear_pattern,
        }
        return inputs, targets

    def _load_and_preprocess_py(
        self,
        image_id_value: object,
        tread_targets_value: object,
        health_target_value: object,
        life_target_value: object,
        wear_target_value: object,
    ) -> tuple[
        Float32Array,
        Float32Array,
        Float32Array,
        Float32Array,
        Float32Array,
        Float32Array,
        np.int32,
    ]:
        """Load and preprocess a single sample on the Python side."""
        image_id = _decode_string_value(image_id_value)
        image = self._load_image(image_id)

        tread_targets = _float_array_from_tensorlike(tread_targets_value)
        tread_mm = tread_targets * np.float32(TREAD_MAX_MM)

        from ai_model.rnn.sequence_builder import build_tread_sequence

        tread_sequence = _as_float32_array(build_tread_sequence(tread_mm.tolist()))
        context = np.zeros(CONTEXT_SIZE, dtype=np.float32)
        health_score = _as_float32_array([_float_from_tensorlike(health_target_value)])
        remaining_life = _as_float32_array([_float_from_tensorlike(life_target_value)])
        wear_pattern = _int_from_tensorlike(wear_target_value)

        return (
            image,
            tread_sequence,
            context,
            tread_targets,
            health_score,
            remaining_life,
            wear_pattern,
        )

    def _load_image(self, image_id: str) -> Float32Array:
        """Load and preprocess a tire image. Returns synthetic data if not found."""
        import importlib
        import cv2

        preprocessing_module: Any = importlib.import_module("ai_model.cnn.preprocessing")
        preprocessing_pipeline: Any = preprocessing_module.run_preprocessing_pipeline

        for extension in (".jpg", ".jpeg", ".png"):
            image_path = self.images_dir / f"{image_id}{extension}"
            if not image_path.exists():
                continue

            image_data: Any = cv2.imread(str(image_path))
            if image_data is None:
                continue

            processed_data: Any = preprocessing_pipeline(
                image_data,
                training=self.training,
                include_edge_channel=True,
            )
            if processed_data is not None:
                return _as_float32_array(processed_data)

        synthetic_image = np.random.normal(
            loc=0.0,
            scale=0.1,
            size=(IMAGE_SIZE[0], IMAGE_SIZE[1], IMAGE_CHANNELS),
        )
        return _as_float32_array(synthetic_image)

    def _synthetic_dataset(self, batch_size: int) -> DatasetType:
        """Generate a purely synthetic dataset for testing or development."""
        logger.warning("Using SYNTHETIC dataset - training on random data!")
        tf_module: Any = tf

        def generator() -> Generator[tuple[InputBatch, TargetBatch], None, None]:
            for _ in range(100):
                inputs: InputBatch = {
                    "image": _as_float32_array(
                        np.random.normal(
                            loc=0.0,
                            scale=1.0,
                            size=(IMAGE_SIZE[0], IMAGE_SIZE[1], IMAGE_CHANNELS),
                        )
                    ),
                    "tread_sequence": _as_float32_array(
                        np.random.normal(loc=0.0, scale=1.0, size=TREAD_SEQUENCE_SHAPE)
                    ),
                    "context": np.zeros(CONTEXT_SIZE, dtype=np.float32),
                }
                targets: TargetBatch = {
                    "tread_depths": _as_float32_array(np.random.uniform(0, 1, (4,))),
                    "health_score": _as_float32_array(np.random.uniform(0, 1, (1,))),
                    "remaining_life": _as_float32_array(np.random.uniform(0, 1, (1,))),
                    "wear_pattern": np.int32(random.randrange(NUM_WEAR_CLASSES)),
                }
                yield inputs, targets

        output_signature = (
            {
                "image": tf.TensorSpec(
                    shape=(IMAGE_SIZE[0], IMAGE_SIZE[1], IMAGE_CHANNELS),
                    dtype=tf.float32,
                ),
                "tread_sequence": tf.TensorSpec(shape=TREAD_SEQUENCE_SHAPE, dtype=tf.float32),
                "context": tf.TensorSpec(shape=(CONTEXT_SIZE,), dtype=tf.float32),
            },
            {
                "tread_depths": tf.TensorSpec(shape=(4,), dtype=tf.float32),
                "health_score": tf.TensorSpec(shape=(1,), dtype=tf.float32),
                "remaining_life": tf.TensorSpec(shape=(1,), dtype=tf.float32),
                "wear_pattern": tf.TensorSpec(shape=(), dtype=tf.int32),
            },
        )

        dataset: DatasetType = tf_module.data.Dataset.from_generator(
            generator,
            output_signature=output_signature,
        )
        return dataset.batch(batch_size).prefetch(tf_module.data.AUTOTUNE)


def build_datasets(
    train_dir: str = "dataset/splits/train",
    val_dir: str = "dataset/splits/validation",
    test_dir: str = "dataset/splits/test",
    images_dir: str = "dataset/raw/tread_images",
    batch_size: int = 16,
) -> dict[str, DatasetType]:
    """
    Build all three dataset splits.

    Reads from:
      dataset/splits/{train,validation,test}/labels.csv
      dataset/raw/tread_images/{safe,moderate,replace}/*.jpg

    Returns:
        Dictionary with `train`, `val`, and `test` dataset pipelines.
    """
    train_ds = SmartTireDataset(train_dir, images_dir, training=True).build(
        batch_size=batch_size,
        shuffle=True,
    )
    val_ds = SmartTireDataset(val_dir, images_dir, training=False).build(
        batch_size=batch_size,
        shuffle=False,
    )
    test_ds = SmartTireDataset(test_dir, images_dir, training=False).build(
        batch_size=batch_size,
        shuffle=False,
    )
    return {"train": train_ds, "val": val_ds, "test": test_ds}
