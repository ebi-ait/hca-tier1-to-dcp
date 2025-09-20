import pytest
import pandas as pd
import os
from unittest.mock import patch, MagicMock
from io import StringIO
import tempfile

from convert_to_dcp import (
    entity_to_tab,
    tab_to_entity,
    make_protocol_name,
    collapse_values,
    ols_label,
    main
)

@pytest.fixture
def sample_metadata_csv():
    data = """sample_id,sample_collection_method,tissue_ontology_term_id,organism_ontology_term_id,sex_ontology_term_id
S1,method1,UBERON:0002107,NCBITaxon:9606,NCIT:C20197
S2,method2,UBERON:0002107,NCBITaxon:10090,NCIT:C20197"""
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.csv') as f:
        f.write(data)
        f.flush()
        yield f.name
        os.unlink(f.name)

@pytest.fixture
def study_metadata_csv():
    data = """0,1
title,Test Study
doi,10.1234/example.doi"""
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.csv') as f:
        f.write(data)
        f.flush()
        yield f.name
        os.unlink(f.name)

def test_tab_entity_roundtrip():
    assert entity_to_tab(tab_to_entity("Cell suspension")) == "Cell suspension"

def test_make_protocol_name():
    val = "Collagenase-D/Dispase"
    expected = "Collagenase-D_Dispase_protocol"
    assert make_protocol_name(val) == expected

def test_collapse_values():
    s = pd.Series(["a", "b", "a"])
    result = collapse_values(s)
    assert result == "a||b"

@pytest.mark.parametrize(
    "term,expected",
    [
        ("NCBITaxon:9606", "Homo sapiens"),
        ("EFO:0003739", "sequencer"),
        ("MONDO:0005383", "panic disorder"),
        ("NCIT:C20197", "Male"),
    ]
)

@patch("convert_to_dcp.requests.get")
def test_ols_label(mock_get, term, expected):
    mock_get.return_value.json.return_value = {"label": expected}
    label = ols_label(term)
    assert label == expected

@patch("convert_to_dcp.get_dcp_template")
@patch("convert_to_dcp.get_dcp_headers")
@patch("convert_to_dcp.fill_missing_ontology_ids")
@patch("convert_to_dcp.fill_ontology_labels")
@patch("convert_to_dcp.check_enum_values")
@patch("convert_to_dcp.export_to_excel")
def test_main_integration(
    mock_export, mock_enum, mock_fill_labels, mock_fill_ids, mock_headers, mock_template,
    sample_metadata_csv, study_metadata_csv
):
    mock_template.return_value = {
        "Project": pd.DataFrame(columns=["project.project_core.project_title"]),
        "Cell suspension": pd.DataFrame(columns=["cell_suspension.biomaterial_core.biomaterial_id"]),
        "Analysis file": pd.DataFrame(columns=[
            "analysis_file.file_core.file_name",
            "analysis_file.file_core.content_description.text",
            "analysis_file.file_core.content_description.ontology",
            "analysis_file.file_core.content_description.ontology_label",
            "analysis_file.file_core.file_source",
            "analysis_file.file_core.format"
        ])
    }
    
    with patch("convert_to_dcp.read_sample_metadata") as mock_sample, \
         patch("convert_to_dcp.read_study_metadata") as mock_study:
        mock_sample.return_value = pd.read_csv(sample_metadata_csv)
        mock_study.return_value = pd.read_csv(study_metadata_csv, header=None).T.drop(0, axis=0)
        
        main(file_path=sample_metadata_csv, local_template=None)
        
        assert mock_export.called, "Expected export_to_excel to be called"