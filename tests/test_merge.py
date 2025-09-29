import pytest
import pandas as pd
import numpy as np

from helper_files.constants.tier2_mapping import TIER2_TO_DCP
from helper_files.merge import (
    LAST_BIOMATERIAL,
    get_fastq_ext,
    get_tab_value,
    get_protocol_id,
    map_key_to_id,
    get_files_per_library,
    check_10x_n_files,
    add_standard_fields,
    merge_file_manifest,
    tab_is_protocol,
    rename_tier2_columns,
    flatten_tier2_spreadsheet,
    merge_overlap,
    merge_sheets,
    merge_tier2_with_dcp
)

@pytest.fixture
def std_dcp_keys():
    return {
        "donor_id": "donor_organism.biomaterial_core.biomaterial_id",
        "sample_id": "specimen_from_organism.biomaterial_core.biomaterial_id",
        "dataset_id": "dataset_id",
        "library_id": LAST_BIOMATERIAL,
        "file_name": "sequence_file.file_core.file_name"
    }

@pytest.fixture
def tier1_spreadsheet():
    return {
        "Tier 1 Dataset Metadata": pd.DataFrame({"dataset_id": ["D1"]}),
        "Tier 1 Donor Metadata": pd.DataFrame({
            "dataset_id": ["D1"], "donor_id": ["donor_1"]
        }),
        "Tier 1 Sample Metadata": pd.DataFrame({
            "sample_id": ["S1"], "donor_id": ["donor_1"], "tissue_ontology_term": ["lung"]
        }),
    }

@pytest.fixture
def tier2_spreadsheet():
    return {
        "Tier 2 Donor Metadata": pd.DataFrame({
            "donor_id": ["donor_1", "donor_2"], "sample_id": ["S1", "S2"], "smoking_status": ["active", "former"]
        }),
        "Additional Genetic Diversity": pd.DataFrame({
            "donor_id": ["donor_1", "donor_2"], "geography_currentresidence_location_country_state": ["Nepal", "Chile"]
        }),
    }

@pytest.fixture
def tier2_renamed_flat():
    return pd.DataFrame({"donor_organism.biomaterial_core.biomaterial_id": ["donor_1", "donor_2"],
                         "specimen_from_organism.biomaterial_core.biomaterial_id": ["S1", "S2"],
                         "donor_organism.medical_history.smoking_status": ["active", "former"],
                         "donor_organism.human_specific.current_residence.location.country_state": ["Nepal", "Chile"]
        })

@pytest.fixture
def file_manifest():
    return pd.DataFrame({
        "file_name": ["sample1.fastq.gz", "sample2.fastq.gz"],
        "library_id": ["S1", "S2"],
    })


@pytest.fixture
def wrangled_spreadsheet(std_dcp_keys):
    return {"Donor organism": pd.DataFrame({std_dcp_keys['donor_id']: ['donor_1', 'donor_2']}),
            "Specimen from organism": pd.DataFrame({std_dcp_keys['sample_id']: ['S1', 'S2'],
                                                    std_dcp_keys['donor_id']: ['donor_1', 'donor_2'],
                                                    'specimen_from_organism.organ.text': ['lung', 'blood']}),
            "Cell suspension": pd.DataFrame({std_dcp_keys['library_id']: ['l1', 'l2'], 
                                             std_dcp_keys['sample_id']: ['S1', 'S2']}),
            "Sequence file": pd.DataFrame({std_dcp_keys['file_name']: ['l1.fastq.gz', 'l2.fastq.gz'], 
                                           std_dcp_keys['library_id']: ['S1', 'S2']}),
            }

@pytest.mark.parametrize("filename,expected", [
    ("foo.fastq.gz", "fastq.gz"),
    ("foo.fq", "fq"),
])

def test_get_fastq_ext_valid(filename, expected):
    assert get_fastq_ext(filename) == expected

@pytest.mark.parametrize("filename", ["fastq.txt", "base_pairs.csv"])
def test_get_fastq_ext_invalid(filename):
    with pytest.raises(KeyError):
        get_fastq_ext(filename)

def test_merge_file_manifest(file_manifest, wrangled_spreadsheet):
    mapping = {"file_name": "sequence_file.file_core.file_name", "library_id": LAST_BIOMATERIAL}
    del wrangled_spreadsheet['Sequence file']['sequence_file.file_core.file_name']
    merged = merge_file_manifest(wrangled_spreadsheet['Sequence file'], file_manifest, mapping)
    assert set(merged.columns) == set(mapping.values())


def test_add_standard_fields(file_manifest, wrangled_spreadsheet):
    mapping = {"file_name": "sequence_file.file_core.file_name", "library_id": LAST_BIOMATERIAL}

    file_manifest = file_manifest.rename(columns=mapping)
    wrangled_spreadsheet['Sequence file'] = merge_overlap(wrangled_spreadsheet['Sequence file'], file_manifest, list(file_manifest.columns), key='sequence_file.file_core.file_name', suffix='fm')
    # add a format column so get_fastq_ext applies
    standard_fields = {"sequence_file.content_description.text": "DNA sequence"}
    wrangled_spreadsheet['Sequence file'] = add_standard_fields(wrangled_spreadsheet['Sequence file'], standard_fields)
    assert all(wrangled_spreadsheet["Sequence file"]["sequence_file.content_description.text"] == "DNA sequence")
    assert all(wrangled_spreadsheet["Sequence file"]["sequence_file.file_core.format"] == "fastq.gz")

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


### TEST MERGE TIER 2


def test_rename_positive():
    df = pd.DataFrame({"Donor_ID": ["donor_1"]})
    mapping = {
        "donor_id": "donor.donor_id"
    }
    out = rename_tier2_columns(df, mapping)
    assert "donor.donor_id" in out.columns


def test_mapping_raises_on_missing():
    df = pd.DataFrame({"unknown": [1]})
    mapping = {}
    with pytest.raises(ValueError):
        rename_tier2_columns(df, mapping)


def test_flatten_merges_tabs():
    tab1 = pd.DataFrame(
        {"donor_id": ["donor"], "sample_id": ["a"], "age": [30]})
    tab2 = pd.DataFrame({"donor_id": ["donor"], "place_of_birth": ["Selinia"]})
    excel_dict = {"Tier 1": tab1, "GDN": tab2}
    out = flatten_tier2_spreadsheet(excel_dict)
    assert "age" in out.columns
    assert "place_of_birth" in out.columns
    assert "sample_id" in out.columns


def test_merge_overlap_prefers_existing(wrangled_spreadsheet, tier2_renamed_flat, std_dcp_keys):
    wrangled_donor = wrangled_spreadsheet['Donor organism']
    wrangled_donor['donor_organism.human_specific.current_residence.location.country_state'] = ['Palestine', np.nan]
    out = merge_overlap(
        wrangled_donor,
        tier2_renamed_flat,
        ["donor_organism.biomaterial_core.biomaterial_id", 
         "donor_organism.medicacl_history.smoking_status", 
         "donor_organism.human_specific.current_residence.location.country_state"],
        key=std_dcp_keys['donor_id'])
    assert out.loc[1, "donor_organism.human_specific.current_residence.location.country_state"] == 'Chile'
    assert out.loc[0, "donor_organism.human_specific.current_residence.location.country_state"] == 'Nepal'


def test_tab_is_protocol():
    assert tab_is_protocol("Library preparation protocol")
    assert not tab_is_protocol("Donor organism")


def test_merge_sheets_protocol():
    key = "dissociation_protocol.protocol_id"
    wrangled_spreadsheet = {
        "Dissociation protocol": pd.DataFrame({
            "dissociation_protocol.protocol_id": ["protocol_1", "protocol_2"],
            "method": [np.nan, "enzymatic"]
        })
    }
    tier2_df = pd.DataFrame({
        "dissociation_protocol.protocol_id":  ["protocol_3"],
        "method": ["mechanical"]
    })
    merged_df = merge_sheets(
        wrangled_spreadsheet,
        tier2_df,
        tab_name="Dissociation protocol",
        field_list=list(tier2_df.columns),
        key=key,
        is_protocol=True
    )
    assert pd.isna(merged_df.loc[merged_df[key] == "protocol_1", "method"].item())
    assert "protocol_3" in merged_df[key].values
    assert merged_df.loc[merged_df[key] == "protocol_2", "method"].item() == "enzymatic"


def test_merge_sheet_non_protocol():
    key = "donor_organism.donor_id"
    wrangled_spreadsheet = {
        "Donor organism": pd.DataFrame({
            "donor_organism.donor_id": ["donor_1", "donor_2", "donor_3"]
        })
    }
    tier2_df = pd.DataFrame({
        "donor_organism.donor_id": ["donor_1", "donor_2", "donor_3"],
        "age": [16, 23, np.nan]
    })
    merged_df = merge_sheets(
        wrangled_spreadsheet,
        tier2_df,
        tab_name="Donor organism",
        field_list=list(tier2_df.columns),
        key=key,
        is_protocol=False
    )
    assert merged_df.loc[merged_df[key] == "donor_2", "age"].item() == 23
    assert pd.isna(merged_df.loc[merged_df[key] == "donor_3", "age"].item())
    assert 16 in merged_df['age'].values

def test_merge_sheets_non_protocol_missing_key_raises():
    wrangled_spreadsheet = {
        "Donor organism": pd.DataFrame({
            "donor_organism.donor_id": ["donor_1"]
        })
    }
    tier2_df = pd.DataFrame({
        "wrong_id": ["donor_1"],
        "age": [30]
    })

    with pytest.raises(ValueError):
        merge_sheets(
            wrangled_spreadsheet,
            tier2_df,
            tab_name="Donor organism",
            field_list=list(tier2_df.columns),
            key="donor_organism.donor_id",
            is_protocol=False
        )

def test_flatten_raises_on_no_common_key():
    tab1 = pd.DataFrame({"donor_id": ["donor_1"], "age": [30]})
    tab2 = pd.DataFrame({"sample_id": ["sample_1"], "storage_time": [1000]})
    tier2_excel = {"Tier2": tab1, "GDN": tab2}

    with pytest.raises(ValueError):
        flatten_tier2_spreadsheet(tier2_excel)

def test_merge_sheets_protocol_empty_tier2():
    key = "dissociation_protocol.protocol_id"
    wrangled_spreadsheet = {
        "Dissociation protocol": pd.DataFrame({
            key: ["protocol_1", "protocol_2"],
            "method": ["enzymatic", "mechanical"]
        })
    }
    tier2_df = pd.DataFrame({
        key: ["protocol_1", "protocol_2"],
        "method": [np.nan, np.nan]
    })

    merged = merge_sheets(
        wrangled_spreadsheet,
        tier2_df,
        tab_name="Dissociation protocol",
        field_list=list(tier2_df.columns),
        key=key,
        is_protocol=True
    )

    # Should be identical to wrangled
    assert list(merged[key]) == ["protocol_1", "protocol_2"]
    assert list(merged["method"]) == ["enzymatic", "mechanical"]


def test_flatten_rename_and_merge():
    # Tier2 Excel dict with 2 tabs
    tier2_excel = {
        "Tier 2": pd.DataFrame({
            "donor_id": ["donor_1"],
            "sample_id": ["sample_1"],
            "age_value": [35]
        }),
        "GD tab": pd.DataFrame({
            "donor_id": ["donor_1"],
            "smoking_pack_years": [12]
        })
    }
    wrangled_spreadsheet = {
        "Donor organism": pd.DataFrame({
            "donor_organism.biomaterial_core.biomaterial_id": ["donor_1"],
            "donor_organism.ncbi_taxon_id": [9606]
        }),
        "Specimen from organism": pd.DataFrame({
            "specimen_from_organism.biomaterial_core.biomaterial_id": ["sample_1"],
            "specimen_from_organism.storage_time": [1]
        })
    }

    tier2_df = flatten_tier2_spreadsheet(tier2_excel)
    tier2_df = rename_tier2_columns(tier2_df, TIER2_TO_DCP)
    merged_df = merge_tier2_with_dcp(tier2_df, wrangled_spreadsheet)

    assert "donor_organism.organism_age" in merged_df['Donor organism'].columns
    assert merged_df['Donor organism'].loc[0, "donor_organism.organism_age"] == 35
    assert merged_df['Donor organism'].loc[0, "donor_organism.biomaterial_core.biomaterial_id"] == "donor_1"
    assert merged_df['Specimen from organism'].loc[0, "specimen_from_organism.biomaterial_core.biomaterial_id"] == "sample_1"
    assert merged_df['Donor organism'].loc[0, "donor_organism.ncbi_taxon_id"] == 9606
    
