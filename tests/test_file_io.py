import pandas as pd
import pytest
from pathlib import Path
from helper_files.file_io import open_spreadsheet, drop_empty_cols

def test_open_spreadsheet_single_sheet(tmp_path):
    df = pd.DataFrame({'donor_id': [1, 2, 3], 'age': [30, 40, 50]})
    file = tmp_path / "test.xlsx"
    df.to_excel(file, sheet_name='Donor', index=False)

    read_df = open_spreadsheet(str(file), tab_name='Donor')

    assert isinstance(read_df, pd.DataFrame)
    assert 'donor_id' in read_df.columns
    assert read_df.shape == (3, 2)

def test_open_spreadsheet_multisheet(tmp_path):
    df1 = pd.DataFrame({'donor_id': ['donor_1', 'donor_2'], 'age': [30, 40]})
    df2 = pd.DataFrame({'sample_id': [10], 'tissue': ['lung'], '': [None]})
    file = tmp_path / "multi.xlsx"

    with pd.ExcelWriter(file) as writer:
        df1.to_excel(writer, sheet_name="Donor", index=False)
        df2.to_excel(writer, sheet_name="Sample", index=False)

    sheets = open_spreadsheet(str(file))

    assert isinstance(sheets, dict)
    assert 'Donor' in sheets and 'Sample' in sheets
    assert sheets['Donor'].shape == (2, 2)
    assert sheets['Sample'].shape == (1, 2)

# ---------------------------
# Tests for drop_empty_cols
# ---------------------------
def test_drop_empty_cols_basic():
    df = pd.DataFrame({
        'Unnamed: 0': [1, 2],
        'index': [3, 4],
        'valid': [5, 6],
        'empty': [None, None]
    })

    cleaned = drop_empty_cols(df)
    assert 'Unnamed: 0' not in cleaned.columns
    assert 'index' not in cleaned.columns
    assert 'empty' not in cleaned.columns
    assert 'valid' in cleaned.columns
