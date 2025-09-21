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
    parser.add_argument("--tier1_path", "-t", action="store",
                        dest="tier1_path", type=str, required=True, help="DCP'ed Tier 1 spreadsheet path")
    parser.add_argument("--wrangled_path", "-w", action="store", 
                        dest="wrangled_path", type=str, required=True, help="Path of previously wrangled project spreadsheet")
    parser.add_argument("--unequal_comparisson", "-u", action="store_false",
                        dest="unequal_comparisson", help="Automaticly continue comparing even if biomaterials are not equal")
    return parser

def main(tier1_path, wrangled_path, unequal_comparisson=False):
    report_dict = init_report_dict()

    tier1_spreadsheet = open_spreadsheet(tier1_path)
    wrangled_spreadsheet = open_spreadsheet(wrangled_path)
    label = get_label(tier1_path)
    
    # Compare number of tabs
    print(f"{BOLD_START}____COMPARE TABS____{BOLD_END}")
    report_dict = compare_n_tabs(tier1_spreadsheet, wrangled_spreadsheet, report_dict)

    # compare number and values of ids for intersect tabs
    print(f"{BOLD_START}____COMPARE IDs____{BOLD_END}")
    for tab in all_entities:
        if tab not in report_dict['tabs']['intersect'] or tab in entity_types['project'] + entity_types['file']:
            # skip project or file tabs since info is not fully recorded in the CxG collection
            continue
            
        # check tab id
        if check_tab_id(tab, wrangled_spreadsheet, tier1_spreadsheet):
            continue
        
        # compare Number and Values of ids per tab
        report_dict = compare_n_ids(tab, report_dict, tier1_spreadsheet, wrangled_spreadsheet, label, unequal_comparisson)
        if not report_dict:
            return
        # Value of ids
        if tab in entity_types['protocol']:
            # for protocol we don't care about matching IDs with tier 1
            continue
        print(f"{BOLD_START}Comparing {tab} IDs:{BOLD_END}")
        report_dict = compare_v_ids(tab, report_dict, tier1_spreadsheet, wrangled_spreadsheet)

    # compare values
    print(f"{BOLD_START}____COMPARE VALUES____{BOLD_END}")
    for tab in all_entities:
        if tab not in report_dict['tabs']['intersect'] or tab in entity_types['project'] + entity_types['file']:
            continue
        print(f"{BOLD_START}Comparing {tab} values:{BOLD_END}")
        report_dict = compare_filled_fields(tab, report_dict, tier1_spreadsheet, wrangled_spreadsheet)

    export_report_json(label, report_dict)

if __name__ == "__main__":
    args = define_parser().parse_args()
    main(tier1_path=args.tier1_path, wrangled_path=args.wrangled_path, 
         unequal_comparisson=args.unequal_comparisson)
