import pandas as pd
import numpy as np
import pytest
from merge_tier2_metadata import (
    tab_is_protocol,
    rename_tier2_columns,
    flatten_tier2_spreadsheet,
    merge_overlap,
    merge_sheets,
    merge_tier2_with_dcp
)

from helper_files.tier2_mapping import TIER2_TO_DCP


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


def test_merge_overlap_prefers_existing():
    wrangled = pd.DataFrame({"sample_id": [
                            "sample_1", "sample_2", "sample_3"], "cell_count": [np.nan, np.nan, 200]})
    tier2 = pd.DataFrame({"sample_id": [
                         "sample_1", "sample_2", "sample_3"], "cell_count": [np.nan, 1000, np.nan]})
    out = merge_overlap(
        wrangled, tier2, ["sample_id", "cell_count"], key="sample_id")
    assert np.isnan(out.loc[0, "cell_count"])
    assert out.loc[1, "cell_count"] == 1000
    assert out.loc[2, "cell_count"] == 200


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
    
