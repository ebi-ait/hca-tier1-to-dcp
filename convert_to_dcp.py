import argparse
import os

from helper_files.convert import (
    read_sample_metadata,
    read_study_metadata,
    get_dcp_template,
    add_doi,
    add_title,
    add_process_locations,
    edit_collection_relative,
    edit_collection_method,
    edit_ncbitaxon,
    edit_sex,
    edit_ethnicity,
    edit_sample_source,
    edit_hardy_scale,
    edit_sampled_site,
    edit_alignment_software,
    edit_dev_stage,
    edit_lib_prep_protocol,
    edit_suspension_type,
    create_protocol_ids,
    fill_ontology_labels,
    fill_missing_ontology_ids,
    check_enum_values,
    populate_spreadsheet,
    add_analysis_file,
    check_required_fields,
    export_to_excel,
)

from helper_files.utils import get_label, BOLD_END, BOLD_START
from helper_files.constants.tier1_mapping import tier1_to_dcp, collection_dict

def define_parser():
    """Defines and returns the argument parser."""
    parser = argparse.ArgumentParser(description="Parser for the arguments")
    parser.add_argument("-ft", "--flat_tier1_spreadsheet", action="store",
                        dest="flat_tier1_spreadsheet", type=str, required=True,
                        help="Flattened tier 1 spreadsheet path")
    parser.add_argument("-o", "--output_dir", action="store",
                        dest="output_dir", type=str, required=False, default='metadata/dt/',
                        help="Directory for the output files")
    parser.add_argument("-lt", "--local_template", action="store",
                        dest="local_template", type=str, required=False,
                        help="Local path of the HCA spreadsheet template")
    return parser

def main(flat_tier1_spreadsheet, output_dir, local_template=None):
    label = get_label(flat_tier1_spreadsheet)
    input_dir = os.path.dirname(flat_tier1_spreadsheet)
    print(f"{BOLD_START}READING FILES{BOLD_END}")
    sample_metadata = read_sample_metadata(label, input_dir)
    study_metadata = read_study_metadata(label, input_dir)
    
    # Edit conditionally mapped fields
    print(f"{BOLD_START}CONVERTING METADATA{BOLD_END}")
    sample_metadata = edit_collection_relative(sample_metadata)
    sample_metadata = edit_ncbitaxon(sample_metadata)
    sample_metadata = edit_sex(sample_metadata)
    sample_metadata = edit_ethnicity(sample_metadata)
    sample_metadata = edit_sample_source(sample_metadata)
    sample_metadata = edit_hardy_scale(sample_metadata)
    sample_metadata = edit_sampled_site(sample_metadata)
    sample_metadata = edit_alignment_software(sample_metadata)
    sample_metadata = edit_lib_prep_protocol(sample_metadata)
    sample_metadata = edit_suspension_type(sample_metadata)
    # sample_metadata = edit_cell_enrichment(sample_metadata) # not yet functional
    sample_metadata = edit_dev_stage(sample_metadata)
    sample_metadata = edit_collection_method(sample_metadata, collection_dict)

    # Rename directly mapped fields
    print(f'\nConverted {"; ".join([col for col in sample_metadata if col in tier1_to_dcp])}')
    dcp_flat = sample_metadata.rename(columns=tier1_to_dcp)
    check_enum_values(dcp_flat)
    
    # Add ontology id and labels
    print('\nPull ontology ids from fields:')
    dcp_flat = fill_missing_ontology_ids(dcp_flat)
    print('\nPull ontology labels from fields:')
    dcp_flat = fill_ontology_labels(dcp_flat)
    
    # Generate spreadsheet
    dcp_spreadsheet = get_dcp_template(local_template)

    dcp_spreadsheet = add_doi(study_metadata, dcp_spreadsheet)
    dcp_spreadsheet = add_title(study_metadata, dcp_spreadsheet)
    
    dcp_flat = create_protocol_ids(dcp_spreadsheet, dcp_flat)

    # Populate spreadsheet
    print(f"{BOLD_START}POPULATING SPREADSHEET{BOLD_END}")
    dcp_spreadsheet = populate_spreadsheet(dcp_spreadsheet, dcp_flat)
    dcp_spreadsheet = add_process_locations(sample_metadata, dcp_spreadsheet)
    dcp_spreadsheet = add_analysis_file(dcp_spreadsheet, label)
    
    check_required_fields(dcp_spreadsheet)

    print(f"{BOLD_START}EXPORTING SPREADSHEET{BOLD_END}")
    export_to_excel(dcp_spreadsheet, output_dir, label, local_template)

BOLD_START = '\033[1m'
BOLD_END = '\033[0;0m'

if __name__ == "__main__":
    args = define_parser().parse_args()
    main(flat_tier1_spreadsheet=args.flat_tier1_spreadsheet, output_dir=args.output_dir, local_template=args.local_template)
