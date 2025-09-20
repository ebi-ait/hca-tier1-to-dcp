import pytest
import pandas as pd
from unittest.mock import patch

from collect_spreadsheet_metadata import flatten_tier1, main

def test_flatten_tier1_merges_correctly():
    dataset_metadata = pd.DataFrame({'dataset_id': [1], 'dataset_col': ['A']})
    donor_metadata = pd.DataFrame({'donor_id': [1], 'dataset_id': [1], 'donor_col': ['B']})
    sample_metadata = pd.DataFrame({'sample_id': [1], 'donor_id': [1], 'dataset_id': [1], 'sample_col': ['C']})

    df = {
        'Tier 1 Dataset Metadata': dataset_metadata,
        'Tier 1 Donor Metadata': donor_metadata,
        'Tier 1 Sample Metadata': sample_metadata
    }

    result = flatten_tier1(df)
    for col in ['sample_id', 'donor_id', 'dataset_id', 'sample_col', 'donor_col', 'dataset_col']:
        assert col in result.columns
    assert result.shape[0] == 1

def test_flatten_tier1_missing_tab_raises():
    df = {'Tier 1 Donor Metadata': pd.DataFrame(), 'Tier 1 Sample Metadata': pd.DataFrame()}
    with pytest.raises(KeyError):
        flatten_tier1(df)

@pytest.fixture
def mock_spreadsheet_data():
    dataset_metadata = pd.DataFrame({
        'dataset_id': [1, 2],
        'dataset_col': ['A', 'B']
    })
    donor_metadata = pd.DataFrame({
        'donor_id': [1, 2],
        'donor_col': ['X', 'Y'],
        'dataset_id': [1, 2]
    })
    sample_metadata = pd.DataFrame({
        'sample_id': [101, 102],
        'donor_id': [1, 2],
        'sample_col': ['foo', 'bar']
    })
    return {
        'Tier 1 Dataset Metadata': dataset_metadata,
        'Tier 1 Donor Metadata': donor_metadata,
        'Tier 1 Sample Metadata': sample_metadata
    }

def test_main_outputs_flattened_df(mock_spreadsheet_data):
    captured_df = None

    # Correct side effect to capture the DataFrame instance
    def fake_to_csv(self, *args, **kwargs):
        nonlocal captured_df
        captured_df = self
        return None

    with patch('collect_spreadsheet_metadata.open_spreadsheet', return_value=mock_spreadsheet_data) as mock_open, \
         patch('collect_spreadsheet_metadata.filename_suffixed', return_value='output.csv') as mock_filename, \
         patch('pandas.DataFrame.to_csv', new=fake_to_csv):

        label = main('testfile.xlsx', '.')

    assert label == 'testfile'

    mock_open.assert_called_once()
    mock_filename.assert_called_once()

    assert captured_df is not None
    assert captured_df.shape[0] == 2  # 2 rows merged
    expected_cols = ['sample_id', 'donor_id', 'dataset_id', 'sample_col', 'donor_col', 'dataset_col']
    for col in expected_cols:
        assert col in captured_df.columns
    first_row = captured_df.iloc[0]
    assert first_row['sample_col'] == 'foo'
    assert first_row['donor_col'] == 'X'
    assert first_row['dataset_col'] == 'A'
