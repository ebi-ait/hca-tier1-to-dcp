from typing import Optional
import os

def filename_suffixed(
    collection_id: str,
    dataset_id: str,
    suffix: str,
    label: Optional[str] = None,
    outdir: str = "metadata",
    ext: str = "csv",
) -> str:
    """
    Build a filename for metadata exports.

    If `label` is given, it overrides collection_id+dataset_id.

    Example:
        filename_suffixed("c1", "d1", "metadata", label=None)
        -> "metadata/c1_d1_metadata.csv"
    """
    basename = f"{label or f'{collection_id}_{dataset_id}'}_{suffix}.{ext}"
    return os.path.join(outdir, basename)
