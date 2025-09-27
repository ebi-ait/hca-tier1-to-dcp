import argparse

from helper_files.constants.tier1_mapping import entity_types, all_entities
from helper_files.utils import open_spreadsheet, get_label, BOLD_END, BOLD_START
from helper_files.compare import (
    check_tab_id,
    export_report_json,
    init_report_dict,
    compare_n_tabs,
    compare_n_ids,
    compare_v_ids,
    compare_filled_fields
)

# Open cellxgene spreadsheet
# Open DCP spreadsheet
    # provide file locally
# Compare number of tabs, use intersection
# Open each common tab 
    # compare number of entites per tab
    # compare ids per tab, for intersection
        # search for Tier 1 ID in DCP name, description, accession
    # compare values of common IDs

def define_parser():
    """Defines and returns the argument parser."""
    parser = argparse.ArgumentParser(description="Parser for the arguments")
    parser.add_argument("-dt", "--dcp_tier1_spreadsheet", action="store",
                        dest="tier1_spreadsheet", type=str, required=True,
                        help="DCP formeted tier 1 spreadsheet path")
    parser.add_argument("-w", "--wrangled_spreadsheet", action="store",
                        dest="wrangled_spreadsheet", type=str, required=True,
                        help="Previously wrangled project spreadsheet path")
    parser.add_argument("-u", "--unequal_comparisson", action="store_false",
                        dest="unequal_comparisson",
                        help="Automaticly continue comparing even if biomaterials are not equal")
    return parser

def main(tier1_spreadsheet, wrangled_spreadsheet, unequal_comparisson=False):
    report_dict = init_report_dict()

    label = get_label(tier1_spreadsheet)
    tier1_df = open_spreadsheet(tier1_spreadsheet)
    wrangled_df = open_spreadsheet(wrangled_spreadsheet)
    
    # Compare number of tabs
    print(f"{BOLD_START}____COMPARE TABS____{BOLD_END}")
    report_dict = compare_n_tabs(tier1_df, wrangled_df, report_dict)

    # compare number and values of ids for intersect tabs
    print(f"{BOLD_START}____COMPARE IDs____{BOLD_END}")
    for tab in all_entities:
        if tab not in report_dict['tabs']['intersect'] or tab in entity_types['project'] + entity_types['file']:
            # skip project or file tabs since info is not fully recorded in the CxG collection
            continue
            
        if check_tab_id(tab, wrangled_df, tier1_df):
            continue
        # compare Number and Values of ids per tab
        report_dict = compare_n_ids(tab, report_dict, tier1_df, wrangled_df, label, unequal_comparisson)
        if not report_dict:
            return
        # Value of ids
        if tab in entity_types['protocol']:
            # for protocol we don't care about matching IDs with tier 1
            continue
        print(f"{BOLD_START}Comparing {tab} IDs:{BOLD_END}")
        report_dict = compare_v_ids(tab, report_dict, tier1_df, wrangled_df)

    # compare values
    print(f"{BOLD_START}____COMPARE VALUES____{BOLD_END}")
    for tab in all_entities:
        if tab not in report_dict['tabs']['intersect'] or tab in entity_types['project'] + entity_types['file']:
            continue
        print(f"{BOLD_START}Comparing {tab} values:{BOLD_END}")
        report_dict = compare_filled_fields(tab, report_dict, tier1_df, wrangled_df)

    export_report_json(label, report_dict)

if __name__ == "__main__":
    args = define_parser().parse_args()
    main(tier1_spreadsheet=args.tier1_spreadsheet, wrangled_spreadsheet=args.wrangled_spreadsheet,
         unequal_comparisson=args.unequal_comparisson)
