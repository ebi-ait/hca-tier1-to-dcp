import os
import pandas as pd
import pytest

from merge_file_manifest import (
    LAST_BIOMATERIAL,
    define_parse,
    get_fastq_ext,
    get_tab_value,
    get_protocol_id,
    map_key_to_id,
    get_files_per_library,
    check_10x_n_files,
    add_standard_fields,
    flatten_tier1,
    merge_file_manifest,
    main
)


@pytest.fixture
def file_manifest():
    return pd.DataFrame({
        "file_name": ["sample1.fastq.gz", "sample2.fastq.gz"],
        "library_id": ["S1", "S2"],
    })


@pytest.fixture
def wrangled_spreadsheet():
    return {"Some tab": pd.DataFrame({"id": [1, 2]})}


@pytest.fixture
def tier1_spreadsheet():
    return {"Tier 1 Dataset Metadata": pd.DataFrame({
        "dataset_id": ["D1"]
        }),
    "Tier 1 Donor Metadata": pd.DataFrame({
        "dataset_id": ["D1"],
        "donor_id": ["donor_1"]
        }),
    "Tier 1 Sample Metadata": pd.DataFrame({
        "sample_id": ["S1"],
        "donor_id": ["donor_1"]
        }),
    }


def test_get_fastq_ext_valid():
    assert get_fastq_ext("foo.fastq.gz") == "fastq.gz"
    assert get_fastq_ext("foo.fq") == "fq"


def test_get_fastq_ext_invalid():
    with pytest.raises(KeyError):
        get_fastq_ext("foo.txt")


def test_merge_file_manifest(file_manifest, wrangled_spreadsheet):
    mapping = {"file_name": "sequence_file.file_core.file_name", "library_id": LAST_BIOMATERIAL}
    merged = merge_file_manifest(wrangled_spreadsheet.copy(), file_manifest, mapping)
    assert "Sequence file" in merged
    assert set(merged["Sequence file"].columns) == set(mapping.values())


def test_add_standard_fields(file_manifest, wrangled_spreadsheet):
    mapping = {"file_name": "sequence_file.file_core.file_name", "library_id": LAST_BIOMATERIAL}
    ws = merge_file_manifest(wrangled_spreadsheet.copy(), file_manifest, mapping)
    # add a format column so get_fastq_ext applies
    standard_fields = {"sequence_file.content_description.text": "DNA sequence"}
    ws2 = add_standard_fields(ws, standard_fields)
    assert all(ws2["Sequence file"]["sequence_file.content_description.text"] == "DNA sequence")
    assert all(ws2["Sequence file"]["sequence_file.file_core.format"] == "fastq.gz")


def test_flatten_tier1(tier1_spreadsheet):
    flat = flatten_tier1(tier1_spreadsheet)
    assert "dataset_id" in flat
    assert "sample_id" in flat
    assert "donor_id" in flat


def test_get_protocol_id():
    key = "random_protocol.protocol_type.text"
    result = get_protocol_id(key)
    assert result == "random_protocol.protocol_core.protocol_id"


def test_get_tab_value():
    key = "library_preparation_protocol.library_construction_method.text"
    result = get_tab_value(key)
    assert result == "Library preparation protocol"


def test_map_key_to_id():
    wrangled = {
        "Assay protocol": pd.DataFrame({
            "assay_protocol.protocol_type.text": ["ATAC-seq"],
            "assay_protocol.protocol_core.protocol_id": ["AP1"]
        })
    }
    result = map_key_to_id("assay_protocol.protocol_type.text", wrangled)
    assert result == {"ATAC-seq": "AP1"}


def test_get_files_per_library():
    df = pd.DataFrame({
        LAST_BIOMATERIAL: ["B1", "B1", "B2"],
        "sequence_file.file_core.file_name": ["f1", "f2", "f3"]
    })
    counts = get_files_per_library(df)
    assert counts["B1"] == 2
    assert counts["B2"] == 1


def test_check_10x_n_files_pass():
    wrangled = {
        "Library preparation protocol": pd.DataFrame({
            "library_preparation_protocol.library_construction_method.text": ["10x v2"],
            "library_preparation_protocol.protocol_core.protocol_id": ["LP1"]
        }),
        "Sequence file": pd.DataFrame({
            LAST_BIOMATERIAL: ["Bio1", "Bio1"],
            "sequence_file.file_core.file_name": ["r1", "r2"],
            "library_preparation_protocol.protocol_core.protocol_id": ["LP1", "LP1"]
        })
    }
    check_10x_n_files(wrangled)


def test_check_10x_n_files_fail():
    wrangled = {
        "Library preparation protocol": pd.DataFrame({
            "library_preparation_protocol.library_construction_method.text": ["10x v2"],
            "library_preparation_protocol.protocol_core.protocol_id": ["LP1"]
        }),
        "Sequence file": pd.DataFrame({
            LAST_BIOMATERIAL: ["Bio1"],
            "sequence_file.file_core.file_name": ["r1"],
            "library_preparation_protocol.protocol_core.protocol_id": ["LP1"]
        })
    }
    with pytest.raises(ValueError):
        check_10x_n_files(wrangled)

