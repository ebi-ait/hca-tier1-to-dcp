import pytest

import convert_to_dcp


@pytest.fixture
def mock_all(mocker):
    """Fixture that mocks all external calls used in main()."""
    fake_sample_metadata = mocker.MagicMock()
    fake_study_metadata = mocker.MagicMock()
    fake_dcp_template = mocker.MagicMock()
    fake_dcp_flat = mocker.MagicMock()
    fake_spreadsheet = mocker.MagicMock()

    mocker.patch.object(convert_to_dcp, "get_label", return_value="fake_label")
    mocker.patch.object(convert_to_dcp, "read_sample_metadata", return_value=fake_sample_metadata)
    mocker.patch.object(convert_to_dcp, "read_study_metadata", return_value=fake_study_metadata)

    for fn in [
        "edit_collection_relative", "edit_ncbitaxon", "edit_sex", "edit_ethnicity",
        "edit_sample_source", "edit_hardy_scale", "edit_sampled_site",
        "edit_alignment_software", "edit_lib_prep_protocol", "edit_suspension_type",
        "edit_dev_stage", "edit_collection_method"
    ]:
        mocker.patch.object(convert_to_dcp, fn, return_value=fake_sample_metadata)

    mocker.patch.object(convert_to_dcp, "check_enum_values")
    mocker.patch.object(convert_to_dcp, "fill_missing_ontology_ids", return_value=fake_dcp_flat)
    mocker.patch.object(convert_to_dcp, "fill_ontology_labels", return_value=fake_dcp_flat)
    mocker.patch.object(convert_to_dcp, "get_dcp_template", return_value=fake_dcp_template)
    mocker.patch.object(convert_to_dcp, "add_doi", return_value=fake_spreadsheet)
    mocker.patch.object(convert_to_dcp, "add_title", return_value=fake_spreadsheet)
    mocker.patch.object(convert_to_dcp, "create_protocol_ids", return_value=fake_dcp_flat)
    mocker.patch.object(convert_to_dcp, "populate_spreadsheet", return_value=fake_spreadsheet)
    mocker.patch.object(convert_to_dcp, "add_process_locations", return_value=fake_spreadsheet)
    mocker.patch.object(convert_to_dcp, "add_analysis_file", return_value=fake_spreadsheet)
    mocker.patch.object(convert_to_dcp, "check_required_fields")
    mocker.patch.object(convert_to_dcp, "export_to_excel")

    return {
        "fake_sample_metadata": fake_sample_metadata,
        "fake_study_metadata": fake_study_metadata,
        "fake_dcp_template": fake_dcp_template,
        "fake_dcp_flat": fake_dcp_flat,
        "fake_spreadsheet": fake_spreadsheet,
    }


def test_main_happy_path(mock_all):
    """End-to-end test of main() with all dependencies mocked."""
    flat_tier1_spreadsheet = "/fake/dir/fake_file.xlsx"
    convert_to_dcp.main(flat_tier1_spreadsheet=flat_tier1_spreadsheet, output_dir='fake/dir', local_template="fake_template.xlsx")

    # Assert export was called at the end
    convert_to_dcp.export_to_excel.assert_called_once()
    # Assert label extraction worked
    convert_to_dcp.get_label.assert_called_once_with(flat_tier1_spreadsheet)
    # Assert metadata readers got correct args
    convert_to_dcp.read_sample_metadata.assert_called_once_with("fake_label", "/fake/dir")
    convert_to_dcp.read_study_metadata.assert_called_once_with("fake_label", "/fake/dir")


def test_define_parser_parses_args():
    """Check that define_parser parses CLI arguments correctly."""
    parser = convert_to_dcp.define_parser()
    args = parser.parse_args([
        "--flat_tier1_spreadsheet", "input.xlsx",
        "--output_dir", "outdir",
        "--local_template", "template.xlsx",
    ])

    assert args.flat_tier1_spreadsheet == "input.xlsx"
    assert args.output_dir == "outdir"
    assert args.local_template == "template.xlsx"
