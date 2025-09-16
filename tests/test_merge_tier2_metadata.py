import pandas as pd
import numpy as np
import pytest
from merge_tier2_metadata import (
    rename_tier2_columns,
    flatten_tier2_spreadsheet,
    merge_overlap,
    merge_sheets,
    tab_is_protocol,
)


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
