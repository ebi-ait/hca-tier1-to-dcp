import os
import re
from pathlib import Path
import pandas as pd

from helper_files.constants.tier1_mapping import KEY_COLS

BOLD_START = '\033[1m'
BOLD_END = '\033[0;0m'

def get_label(filename: str) -> str:
    label = Path(filename).stem  # strip extension
    label = re.sub(r'hca[_\s-]*tier[_\s-]*1[_\s-]*metadata', '', label, flags=re.I)
    label = re.sub(r'_dcp|_tier1|_cell_obs|_study_metadata', '', label, flags=re.I)
    label = re.sub(r'[_\s-]*metadata([_\s-]*\d{1,2}[_\s-]*\d{1,2}[_\s-]*\d{2,4})?$', '', label, flags=re.I)
    label = re.sub(r'[_\s]+', '_', label)
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
    if df[tab_name].iloc[0].str.match(donor_field).any() and \
        (df[tab_name].iloc[3,0] == 'FILL OUT INFORMATION BELLOW THIS ROW' or \
         df[tab_name].iloc[3].str.len().sum() == 0):
        return [1, 2, 3, 4]
    # dcp-to-tier1 format
    # df[tab_name].iloc[3].str.match(donor_field).any()
    return None
    
def drop_empty_cols(df):
    df = df.dropna(axis=1, how='all')
    index_like_cols = [col for col in df.columns if str(col).lower().startswith("unnamed") or str(col).lower() == "index"]
    df = df.drop(columns=index_like_cols, errors='ignore')
    return df

def check_empty_sheet(df):
    if isinstance(df, pd.DataFrame):
        return df.empty
    return any(tab.empty for tab in df.values())

def merge_same_key_tabs(df):
    # check if two donor level tabs and merge (for T2 metadata)
    for key in KEY_COLS:
        col = key.replace('_id', '')
        tab_keys_match = [tab for tab in df.keys() if col.lower() in tab.lower()]
        if len(tab_keys_match) <= 1:
            continue
        for tab in tab_keys_match[1:]:
            df[tab_keys_match[0]] = df[tab_keys_match[0]].merge(df[tab], how='inner', on=key)
            df.pop(tab)
    return df


def open_spreadsheet(spreadsheet_path, tab_name=None):
    if not os.path.exists(spreadsheet_path):
        raise FileNotFoundError(f"File not found at {spreadsheet_path}")
    skiprows = detect_excel_format(spreadsheet_path)
    df = pd.read_excel(
        spreadsheet_path,
        sheet_name=tab_name,
        skiprows=skiprows,
        index_col=None
    )
    if not tab_name and 'Donor organism' not in df:
        df = merge_same_key_tabs(df)
    if 'validation_sheet' in df:
        df.pop('validation_sheet')
    if check_empty_sheet(df):
        raise ValueError(f'Spreadsheet {spreadsheet_path} has empty sheet')
    return drop_empty_cols(df) if tab_name else {k: drop_empty_cols(d) for k, d in df.items() if not d.empty}
