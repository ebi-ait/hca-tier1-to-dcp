import argparse
import os

from helper_files.convert import (
    read_sample_metadata,
    read_study_metadata,
    get_dcp_template,
    add_doi,
    add_title,
    add_process_locations,
    edit_all_sample_metadata,
    create_protocol_ids,
    fill_ontologies,
    check_enum_values,
    populate_spreadsheet,
    add_analysis_file,
    check_required_fields,
    export_to_excel,
    flatten_tiered_spreadsheet
)
from helper_files.merge import (
    manual_fixes,
    rename_tier2_columns
)

from helper_files.utils import get_label, BOLD_END, BOLD_START, open_spreadsheet
from helper_files.constants.tier1_mapping import tier1_to_dcp, collection_dict, KEY_COLS
from helper_files.constants.tier2_mapping import TIER2_TO_DCP, TIER2_TO_DCP_UPDATE

def define_parser():
    """Defines and returns the argument parser."""
    parser = argparse.ArgumentParser(description="Parser for the arguments")
    parser.add_argument("-ft", "--flat_tier1_spreadsheet", action="store",
                        dest="flat_tier1_spreadsheet", type=str, required=True,
                        help="Flattened tier 1 spreadsheet path")
    parser.add_argument("-t2", "--tier2_spreadsheet", action="store",
                        dest="tier2_spreadsheet", type=str, required=False,
                        help="Tier 2 spreadsheet path")
    parser.add_argument("-o", "--output_dir", action="store",
                        dest="output_dir", type=str, required=False, default='metadata/dt/',
                        help="Directory for the output files")
    parser.add_argument("-lt", "--local_template", action="store",
                        dest="local_template", type=str, required=False,
                        help="Local path of the HCA spreadsheet template")
    return parser

def main(flat_tier1_spreadsheet, tier2_spreadsheet=None, output_dir='metadata/dt/', local_template=None):
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
    
    # flatten t2
    if tier2_spreadsheet:
        tier2_df = open_spreadsheet(tier2_spreadsheet)
        
        all_tier2 = {**TIER2_TO_DCP, **TIER2_TO_DCP_UPDATE}
        tier2_flat = flatten_tiered_spreadsheet(tier2_df, merge_type='outer')
        tier2_low_key = tier1_to_dcp[next(id for id in KEY_COLS if id in tier2_flat.columns)]
        tier2_flat = manual_fixes(tier2_flat)
        tier2_flat = rename_tier2_columns(tier2_flat, all_tier2)
        dcp_flat = dcp_flat.merge(tier2_flat, how='outer', on=tier2_low_key, suffixes=('_dcp', ''))
    # Add ontology id and labels
    dcp_flat = fill_ontologies(dcp_flat)
    
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
    export_to_excel(dcp_spreadsheet, output_dir, label, local_template, t2=bool(tier2_spreadsheet))

if __name__ == "__main__":
    args = define_parser().parse_args()
    main(flat_tier1_spreadsheet=args.flat_tier1_spreadsheet, 
         tier2_spreadsheet=args.tier2_spreadsheet, 
         output_dir=args.output_dir, 
         local_template=args.local_template)
