import os
from unittest import mock

import pandas as pd
import pytest

from collect_cellxgene_metadata import main
from tests.test_collect import dummy_collection


@mock.patch("anndata.read_h5ad")
@mock.patch("collect_cellxgene_metadata.download_h5ad_file")
@mock.patch("collect_cellxgene_metadata.get_collection_data")
def test_main_integration_real_extract(mock_get_collection, mock_download, mock_read, tmp_path, dummy_collection):
    dummy_collection_copy = dummy_collection.copy()
    mock_get_collection.return_value = dummy_collection_copy


    # Fake AnnData with obs
    obs_df = pd.DataFrame({
    "library_id": ["lib1"],
    "donor_id": ["don1"],
    "tissue_free_text": ["lung"],
    })
    adata = mock.Mock()
    adata.obs = obs_df
    mock_read.return_value = adata


    # Run main
    main(collection_id="cid", dataset_id="ds1", output_dir=str(tmp_path))


    # Check files
    files = os.listdir(tmp_path)
    assert any(f.endswith("_study_metadata.csv") for f in files), "study_metadata file should be created"
    assert any(f.endswith("_metadata.csv") for f in files), "metadata file should be created by extract"
    assert any(f.endswith("_cell_obs.csv") for f in files), "cell_obs file should be created by extract"


    obs_file = [f for f in files if f.endswith("_metadata.csv") and '_study_' not in f][0]
    content = pd.read_csv((tmp_path / obs_file))
    assert "library_id" in content
    assert content.loc[0, "tissue_free_text"]