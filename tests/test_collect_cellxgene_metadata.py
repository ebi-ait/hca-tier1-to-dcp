import os
import pandas as pd
import pytest

import collect_cellxgene_metadata
from tests.test_collect import dummy_collection

@pytest.fixture
def mock_all(mocker, dummy_collection):
    """Fixture that mocks external dependencies for collect_cellxgene_metadata.main."""
    dummy_collection_copy = dummy_collection.copy()

    mock_get_collection = mocker.patch.object(
        collect_cellxgene_metadata, "get_collection_data", return_value=dummy_collection_copy
    )
    mock_download = mocker.patch.object(
        collect_cellxgene_metadata, "download_h5ad_file"
    )

    # Fake AnnData object with obs DataFrame
    obs_df = pd.DataFrame({
        "library_id": ["lib1"],
        "donor_id": ["don1"],
        "tissue_free_text": ["lung"],
    })
    fake_adata = mocker.MagicMock()
    fake_adata.obs = obs_df

    mock_read = mocker.patch("anndata.read_h5ad", return_value=fake_adata)

    return {
        "mock_get_collection": mock_get_collection,
        "mock_download": mock_download,
        "mock_read": mock_read,
        "fake_obs_df": obs_df,
    }


def test_main_integration_real_extract(mock_all, tmp_path):
    # Run main with mocked dependencies
    label = collect_cellxgene_metadata.main(
        collection_id="cid", dataset_id="ds1", output_dir=str(tmp_path)
    )

    # Check output files exist
    files = os.listdir(tmp_path)
    assert any(f.endswith("_study_metadata.csv") for f in files), "study_metadata file should be created"
    assert any(f.endswith("_metadata.csv") for f in files), "metadata file should be created by extract"
    assert any(f.endswith("_cell_obs.csv") for f in files), "cell_obs file should be created by extract"

    # Validate metadata content
    obs_file = [f for f in files if f.endswith("_metadata.csv") and "_study_" not in f][0]
    content = pd.read_csv(tmp_path / obs_file)

    assert "library_id" in content
    assert content.loc[0, "tissue_free_text"]
    assert label == 'cid_ds1'
