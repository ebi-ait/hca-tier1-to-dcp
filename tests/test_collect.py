import os
from unittest import mock

import pandas as pd
import pytest

from helper_files.collect import (
    generate_collection_report,
    selection_of_dataset,
    get_collection_data,
    download_h5ad_file,
    extract_and_save_metadata,
    doi_search_ingest
)


@pytest.fixture
def dummy_collection():
    return {
        "name": "Test Collection",
        "collection_url": "http://example.com",
        "visibility": "public",
        "doi": "10.1234/example",
        "consortia": ["ABC"],
        "contact_name": "John Doe",
        "contact_email": "john@example.com",
        "links": [{"link_type": "PROTOCOL", "link_url": "http://example.com/protocol"}],
        "datasets": [
            {
                "dataset_id": "ds1",
                "cell_count": 1000,
                "title": "Dataset 1",
                "assets": [{"filetype": "H5AD", "url": "http://example.com/file.h5ad"}],
            }
        ],
    }


def test_generate_collection_report(dummy_collection):
    report = generate_collection_report(dummy_collection)
    assert report["name"] == "Test Collection"
    assert "consortia" in report


def test_selection_of_dataset_preselected(dummy_collection, capsys):
    ds_id = selection_of_dataset(dummy_collection, dataset_id="ds1")
    assert ds_id == "ds1"
    captured = capsys.readouterr()
    assert "Pre-selected dataset" in captured.out


def test_selection_of_dataset_single_choice(dummy_collection, monkeypatch):
    # Only one dataset so it should auto-select without user input
    result = selection_of_dataset(dummy_collection, None)
    assert result == "ds1"


@mock.patch("requests.get")
def test_get_collection_data(mock_get, dummy_collection):
    mock_get.return_value.json.return_value = dummy_collection
    mock_get.return_value.raise_for_status.return_value = None
    data = get_collection_data("cid")
    assert data["name"] == "Test Collection"


@mock.patch("requests.get")
def test_download_h5ad_file(mock_get, tmp_path):
    # Mock response stream
    fake_content = b"12345"
    mock_resp = mock.Mock()
    mock_resp.iter_content = lambda chunk_size: [fake_content]
    mock_resp.headers = {"Content-Length": str(len(fake_content))}
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value.__enter__.return_value = mock_resp

    out_file = tmp_path / "test.h5ad"
    download_h5ad_file("http://example.com/file.h5ad", str(out_file))
    assert out_file.exists()
    assert out_file.read_bytes() == fake_content


@mock.patch("anndata.read_h5ad")
def test_extract_and_save_metadata(mock_read, tmp_path, dummy_collection):
    # Mock AnnData object
    obs_df = pd.DataFrame({
        "library_id": ["lib1"],
        "donor_id": ["don1"],
        "tissue": ["lung"],
    })
    adata = mock.Mock()
    adata.obs = obs_df

    mock_read.return_value = adata

    extract_and_save_metadata(adata, "cid", "ds1", output_dir=str(tmp_path))
    files = os.listdir(tmp_path)
    assert any("metadata" in f for f in files)
    assert any("cell_obs" in f for f in files)


@mock.patch("requests.post")
@mock.patch("requests.get")
def test_doi_search_ingest_found(mock_get, mock_request):
    mock_get.return_value.ok.return_value = True
    mock_get.return_value.json.return_value = {"Message": "UUID not found"}
    mock_request.return_value.json.return_value = {
        "_embedded": {
            "projects": [
                {
                    "uuid": {"uuid": "uuid1"},
                    "_links": {"self": {"href": "http://ingest/uuid1"}},
                }
            ]
        }
    }
    mock_request.return_value.raise_for_status.return_value = None
    doi_search_ingest("10.1234/example", token="fake")
