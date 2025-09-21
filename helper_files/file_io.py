import os
import re
import pandas as pd
from pathlib import Path
from typing import Optional

def get_label(filename: str) -> str:
    label = Path(filename).stem  # strip extension
    label = re.sub(r'hca[_\s-]*tier[_\s-]*1[_\s-]*metadata', '', label, flags=re.I)
    label = re.sub(r'_dcp|_cell_obs|_study_metadata', '', label, flags=re.I)
    label = re.sub(r'[_\s-]*metadata([_\s-]*\d{1,2}[_\s-]*\d{1,2}[_\s-]*\d{2,4})?$', '', label, flags=re.I)
    label = re.sub(r'[_\s-]+', '_', label)
    return label.strip('_')

def filename_suffixed(
    dir_name: str, 
    label: str,
    suffix: str,
    ext: str = "csv"
    ) -> str:
    basename = f"{label}_{suffix}.{ext}"
    return os.path.join(dir_name, basename)

def detect_excel_format(spreadsheet_path, tab_name=None):
    """DCP, HLCA, Gut, Tracker and dcp-to-tier1 use small variations of the DCP spreadsheet.
    here we want to detect which variation is automatically and open to have programmatic name as header and from row 1+ the values"""
    df = pd.read_excel(spreadsheet_path, sheet_name=None, nrows=10, header=None)

    donor_file_tab = re.compile(r'donor', re.IGNORECASE)
    tab_name = next((k for k in df.keys() if donor_file_tab.search(k)), list(df.keys())[0]) if not tab_name else tab_name
    df = {k: d.fillna('').astype(str) for k,d in df.items()}

    if len(df[tab_name]) < 4:
        # if less than 3 rows in sheet, dcp headers are missing, so it's dcp-to-tier1 format
        return None

    # DCP/ HLCA Tier 1 format
    donor_field = re.compile(r'^donor_id$|^donor_organism.biomaterial_core.biomaterial_id|file_name$', re.IGNORECASE)
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