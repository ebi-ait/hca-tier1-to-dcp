import os
import re
import pandas as pd
from typing import Optional

def filename_suffixed(
    collection_id: str, dataset_id: str,
    suffix: str, label: Optional[str] = None,
    outdir: str = "metadata", ext: str = "csv") -> str:
    basename = f"{label or f'{collection_id}_{dataset_id}'}_{suffix}.{ext}"
    return os.path.join(outdir, basename)

def detect_excel_format(spreadsheet_path):
    """DCP, HLCA, Gut, Tracker and dcp-to-tier1 use small variations of the DCP spreadsheet.
    here we want to detect which variation is automatically and open to have programmatic name as header and from row 1+ the values"""
    df = pd.read_excel(spreadsheet_path, sheet_name=None, nrows=10, header=None)

    donor_tab = re.compile(r'donor', re.IGNORECASE)
    tab_name = next((k for k in df.keys() if donor_tab.search(k)), list(df.keys())[0])

    # DCP/ HLCA Tier 1 format
    donor_field = re.compile(r'^donor_id$|^donor_organism.biomaterial_core.biomaterial_id$', re.IGNORECASE)
    if df[tab_name].iloc[3].str.match(donor_field).any():
        return [0, 1, 2, 4]
    # Gut format
    if df[tab_name].iloc[3].str.len().sum() == 0 and df[tab_name].iloc[0].str.match(donor_field).any():
        return [1, 2, 3, 4]
    # dcp-to-tier1 format
    # df[tab_name].iloc[3].str.match(donor_field).any()
    return None
    
def drop_empty_cols(df):
    df = df.dropna(axis=1, how='all')
    index_like_cols = [col for col in df.columns if str(col).lower().startswith("unnamed") or str(col).lower() == "index"]
    df = df.drop(columns=index_like_cols, errors='ignore')
    return df

def open_spreadsheet(spreadsheet_path, tab_name=None):
    if not os.path.exists(spreadsheet_path):
        raise FileNotFoundError(f"File not found at {spreadsheet_path}")
    skiprows = detect_excel_format(spreadsheet_path)
    try:
        df = pd.read_excel(
            spreadsheet_path,
            sheet_name=tab_name,
            skiprows=skiprows,
            index_col=None
        )
        return drop_empty_cols(df) if tab_name else {k: drop_empty_cols(d) for k, d in df.items()}
    except Exception as e:
        raise ValueError(
            f"Error reading spreadsheet file: {e} for {spreadsheet_path}"
        ) from e