import os
from unittest.mock import patch
import tempfile

import pytest
import pandas as pd

from helper_files.convert import (
    entity_to_tab,
    tab_to_entity,
    make_protocol_name,
    collapse_values,
    ols_label
)

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

@patch("helper_files.convert.requests.get")
def test_ols_label(mock_get, term, expected):
    mock_get.return_value.json.return_value = {"label": expected}
    label = ols_label(term)
    assert label == expected
