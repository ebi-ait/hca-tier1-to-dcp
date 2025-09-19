import pandas as pd
import pytest
from pathlib import Path
from helper_files.file_io import open_spreadsheet, drop_empty_cols, detect_excel_format

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

def test_detect_excel_format_dcp(tmp_path):
    df1 = pd.DataFrame({'donor_organism.biomaterial_core.biomaterial_id': [donor]})

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

def create_excel_for_format(tmp_path, filename, rows, sheet_name="Donor"):
    """rows: list of lists representing rows to write in sheet"""
    df = pd.DataFrame(rows)
    file_path = tmp_path / filename
    df.to_excel(file_path, sheet_name=sheet_name, index=False, header=False)
    return str(file_path)

def test_detect_excel_format_dcp(tmp_path):
    # Row 0-4: metadata/description, row 3 has donor_id
    rows = [
        ["Donor ID", "Organism Age", "Biological Sex"],
        ["A biomaterial identifier", "Age at the time of collection", "Biological sex"],
        ["donor_1", "12; 24; 46", "female; intersex"],
        ["donor_id", "age", "sex"],
        ["FILL OUT INFORMATION BELOW THIS ROW", "", ""]
    ]
    file_path = create_excel_for_format(tmp_path, "dcp.xlsx", rows)
    skiprows = detect_excel_format(file_path)
    assert skiprows == [0, 1, 2, 4]

def test_detect_excel_format_gut(tmp_path):
    # Row 0: donor_id, row 1-4: description
    rows = [
        ["donor_id", "age", "sex"],
        ["a unique identifier for the donor", "age of the subject", "Reported sex of the donor"],
        ["", "5; 10; 10-15", "female"],
        ["", "", ""],
        ["FILL OUT INFORMATION BELOW THIS ROW", "", ""]
    ]
    file_path = create_excel_for_format(tmp_path, "gut.xlsx", rows)
    skiprows = detect_excel_format(file_path)
    assert skiprows == [1, 2, 3, 4]

def test_detect_excel_format_dcp_to_tier1(tmp_path):
    # Row 0: donor_id, no description rows
    rows = [
        ["donor_id", "age", "sex"],
        ["donor1", 33, "M"],
        ["patient2", 37, "M"],
        ["reafra3", 32, "F"],
        ["subject4", 40, "F"]
    ]
    file_path = create_excel_for_format(tmp_path, "dcp_to_tier1.xlsx", rows)
    skiprows = detect_excel_format(file_path)
    assert skiprows is None
