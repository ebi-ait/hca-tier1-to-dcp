import argparse
import os
import pandas as pd

from helper_files.constants.file_mapping import FILE_MANIFEST_MAPPING
from helper_files.convert import (
    read_sample_metadata,
    read_study_metadata,
    get_dcp_template,
    add_doi,
    add_title,
    edit_all_sample_metadata,
    create_protocol_ids,
    fill_ontologies,
    check_enum_values,
    populate_spreadsheet,
    add_analysis_file,
    check_required_fields,
    export_to_excel,
    tiered_suffix
)
from helper_files.merge import merge_file_manifest_with_flat_dcp, merge_tier2_with_flat_dcp

from helper_files.utils import get_label, BOLD_END, BOLD_START
from helper_files.constants.tier1_mapping import tier1_to_dcp, collection_dict

def define_parser():
    """Defines and returns the argument parser."""
    parser = argparse.ArgumentParser(description="Parser for the arguments")
    parser.add_argument("-ft", "--flat_tier1_spreadsheet", action="store",
                        dest="flat_tier1_spreadsheet", type=str, required=True,
                        help="Flattened tier 1 spreadsheet path")
    parser.add_argument("-t2", "--tier2_spreadsheet", action="store",
                        dest="tier2_spreadsheet", type=str, required=False,
                        help="Tier 2 spreadsheet path")
    parser.add_argument("-fm", "--file_manifest", action='store', 
                        dest="file_manifest", type=str, required=False,
                        help="File manifest path")
    parser.add_argument("-o", "--output_dir", action="store",
                        dest="output_dir", type=str, required=False, default='metadata/dt/',
                        help="Directory for the output files")
    parser.add_argument("-s", "--skip", action="store_true",
                        dest="skip", required=False,
                        help="Skip auto OLS ontology filling step")
    parser.add_argument("-lt", "--local_template", action="store",
                        dest="local_template", type=str, required=False,
                        help="Local path of the HCA spreadsheet template")
    return parser

def main(flat_tier1_spreadsheet, tier2_spreadsheet=None, file_manifest=None, output_dir='metadata/dt/', skip=False, local_template=None):
    label = get_label(flat_tier1_spreadsheet)
    input_dir = os.path.dirname(flat_tier1_spreadsheet)
    print(f"{BOLD_START}READING FILES{BOLD_END}")
    sample_metadata = read_sample_metadata(label, input_dir)
    study_metadata = read_study_metadata(label, input_dir)
    
    # Edit conditionally mapped fields
    print(f"{BOLD_START}CONVERTING METADATA{BOLD_END}")
    sample_metadata = edit_all_sample_metadata(sample_metadata, collection_dict)
    print(f'\nConverted {"; ".join([col for col in sample_metadata if col in tier1_to_dcp])}')

    # Rename directly mapped fields
    dcp_flat = sample_metadata.rename(columns=tier1_to_dcp)
    check_enum_values(dcp_flat)
    
    # add t2
    if pd.notna(tier2_spreadsheet):
        print(f"{BOLD_START}MERGING TIER 2 METADATA{BOLD_END}")
        dcp_flat = merge_tier2_with_flat_dcp(tier2_spreadsheet, dcp_flat, tier1_to_dcp)
    # file manifest
    if pd.notna(file_manifest):
        print(f"{BOLD_START}MERGING FILE MANIFEST METADATA{BOLD_END}")
        dcp_flat = merge_file_manifest_with_flat_dcp(dcp_flat, file_manifest, FILE_MANIFEST_MAPPING)
    # Add ontology id and labels
    if not skip:
        print(f"{BOLD_START}FILLING ONTOLOGIES{BOLD_END}")
        dcp_flat = fill_ontologies(dcp_flat)
        dcp_flat = add_analysis_file(dcp_flat, label)
    
    # Generate spreadsheet
    dcp_spreadsheet = get_dcp_template(local_template)

    dcp_spreadsheet = add_doi(study_metadata, dcp_spreadsheet)
    dcp_spreadsheet = add_title(study_metadata, dcp_spreadsheet)
    
    dcp_flat = create_protocol_ids(dcp_spreadsheet, dcp_flat)

    # Populate spreadsheet
    print(f"{BOLD_START}POPULATING SPREADSHEET{BOLD_END}")
    dcp_spreadsheet = populate_spreadsheet(dcp_spreadsheet, dcp_flat)
    
    check_required_fields(dcp_spreadsheet)

    print(f"{BOLD_START}EXPORTING SPREADSHEET{BOLD_END}")
    export_to_excel(dcp_spreadsheet, output_dir, label, local_template, 
                    suffix=tiered_suffix(tier2_spreadsheet, file_manifest))

if __name__ == "__main__":
    args = define_parser().parse_args()
    main(flat_tier1_spreadsheet=args.flat_tier1_spreadsheet,
         tier2_spreadsheet=args.tier2_spreadsheet,
         file_manifest=args.file_manifest,
         output_dir=args.output_dir,
         skip=args.skip,
         local_template=args.local_template)
