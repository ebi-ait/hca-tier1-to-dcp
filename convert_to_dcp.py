import argparse
import os
import io
import re
import sys
import requests
from requests.exceptions import ConnectionError

import pandas as pd
from numpy import nan

from tier1_mapping import tier1_to_dcp


def define_parser():
    """Defines and returns the argument parser."""
    parser = argparse.ArgumentParser(description="Parser for the arguments")
    parser.add_argument("--collection", "-c", action="store",
                        dest="collection_id", type=str, required=True, help="Collection id")
    parser.add_argument("--dataset", "-d", action="store",
                        dest="dataset_id", type=str, required=False, help="Dataset id")
    return parser


def read_study(collection_id, dataset_id):
    try:
        metadata_path = f"metadata/{collection_id}_{dataset_id}_study_metadata.csv"
        metadata = pd.read_csv(metadata_path, header=None).T
        metadata.columns = metadata.iloc[0]
        return metadata.drop(0, axis=0)
    except FileNotFoundError:
        print(f"File not found: {metadata_path}")
        return pd.DataFrame()


def get_dcp_spreadsheet(local_path=None):
    # if no internet connection, provide local path
    hca_template_url = 'https://github.com/ebi-ait/geo_to_hca/raw/master/template/hca_template.xlsx'
    path = local_path if local_path else hca_template_url
    try:
        return pd.read_excel(path, sheet_name=None, skiprows=[0, 1, 2, 4])
    except FileNotFoundError:
        print(f"Local file path not found: {local_path}")
        return {}

def get_dcp_headers(local_path=None):
    # if no internet connection, provide local path
    hca_template_url = 'https://github.com/ebi-ait/geo_to_hca/raw/master/template/hca_template.xlsx'
    path = local_path if local_path else hca_template_url
    try:
        dcp_headers = pd.read_excel(hca_template_url, sheet_name=None, header=None)
    except FileNotFoundError:
        print(f"Local file path not found: {local_path}")
        return {}
    for tab in dcp_headers:
        dcp_headers[tab].rename(columns=dcp_headers[tab].iloc[3], inplace= True)
    return dcp_headers

## Project
def add_doi(study_metadata, dcp_spreadsheet):
    # TODO pull title and authors from any DOI api i.e. https://api.crossref.org/swagger-ui/index.html#/Works/get_works__doi_
    if 'doi' in study_metadata.columns:
        dois = pd.DataFrame({'project.publications.doi': list(set(study_metadata['doi']))})
        dcp_spreadsheet['Project - Publications'] = pd.concat([dcp_spreadsheet['Project - Publications'], dois], ignore_index=True)
    return dcp_spreadsheet

def add_title(study_metadata, dcp_spreadsheet):
    if 'title' in study_metadata:
        if len(set(study_metadata['title'])) != 1:
            print(f"We have multiple titles {set(study_metadata['title'])}")
        titles = pd.DataFrame({'project.project_title'})
        dcp_spreadsheet['Project'] = pd.concat([dcp_spreadsheet['Project'], titles])
    return dcp_spreadsheet

def add_institute(sample_metadata, dcp_spreadsheet):
    # TODO add institute per sample after sample identification
    if 'institute' in sample_metadata.columns and len(set(sample_metadata['institute'])) == 1:
        dcp_spreadsheet['Cell suspension']['process.process_core.location'] = sample_metadata['institute'].iloc[0]
    return dcp_spreadsheet

# Get the ontology label instead of ontology id from OLS4
def ols_label(ontology_id, only_label=True, ontology=None):
    if not re.match(r"\w+:\d+", ontology_id):
        return ontology_id
    ontology_name = ontology if ontology else ontology_id.split(":")[0].lower()
    ontology_term = ontology_id.replace(":", "_")
    response = requests.get(f'https://www.ebi.ac.uk/ols4/api/ontologies/{ontology_name}/terms/http%253A%252F%252Fpurl.obolibrary.org%252Fobo%252F{ontology_term}')
    try:
        results = response.json()
    except ConnectionError as e:
        print(e)
    return results['label'] if only_label else results

## Edit sample_metadata
def edit_collection_relative(sample_metadata):
    if 'sample_collection_relative_time_point' in sample_metadata:
        number_pattern = '([\\d]+[.|\\,]?\\d?)'
        sample_metadata['specimen_from_organism.biomaterial_core.timecourse.value'] = \
            sample_metadata['sample_collection_relative_time_point'].str.extract(number_pattern, expand=False)
        sample_metadata.loc[sample_metadata['sample_collection_relative_time_point'].notna(), 'specimen_from_organism.biomaterial_core.timecourse.relevance'] = 'relative time of collection'
        time_units_pattern = r'(hour|day|week|month|year)'
        sample_metadata['specimen_from_organism.biomaterial_core.timecourse.unit.text'] = \
            sample_metadata['sample_collection_relative_time_point'].str.extract(time_units_pattern, expand=False)
    return sample_metadata

def tissue_type_taxon(sample_metadata, tissue_type, tissue_type_dcp):
    sample_metadata.loc[sample_metadata['tissue_type'] == tissue_type, tissue_type_dcp[tissue_type]] = \
        sample_metadata.loc[sample_metadata['tissue_type'] == tissue_type, 'organism_ontology_term_id'].str.removeprefix('NCBITaxon:')
    return sample_metadata

def edit_ncbitaxon(sample_metadata):
    tissue_type_dcp = {
        'tissue': 'cell_suspension.biomaterial_core.ncbi_taxon_id',
        'cell culture': 'cell_line.biomaterial_core.ncbi_taxon_id',
        'organoid': 'organoid.biomaterial_core.ncbi_taxon_id'
    }

    if 'organism_ontology_term_id' in sample_metadata:
        sample_metadata['donor_organism.biomaterial_core.ncbi_taxon_id'] = sample_metadata['organism_ontology_term_id'].str.removeprefix('NCBITaxon:')
        sample_metadata['specimen_from_organism.biomaterial_core.ncbi_taxon_id'] = sample_metadata['organism_ontology_term_id'].str.removeprefix('NCBITaxon:')
        if 'tissue_type' in sample_metadata:
            for tissue_type in tissue_type_dcp.keys():
                if tissue_type in sample_metadata['tissue_type'].values:
                    sample_metadata = tissue_type_taxon(sample_metadata, tissue_type, tissue_type_dcp)
    return sample_metadata

def edit_sex(sample_metadata):
    # sex_ontology_dict = {
    #         'PATO:0000383': 'female',
    #         'PATO:0000384': 'male'
    # }
    if 'sex_ontology_term_id' in sample_metadata:
        sample_metadata['donor_organism.sex'] = sample_metadata['sex_ontology_term_id'].apply(ols_label)
        if not sample_metadata['donor_organism.sex'].isin(['female', 'male']).all():
            print(f"Unsupported sex value {sample_metadata.loc['sex_ontology_term_id', ~sample_metadata['donor_organism.sex'].isin(['female', 'male'])]}")
    return sample_metadata

def edit_sample_source(sample_metadata):
    if 'sample_source' in sample_metadata:
        sample_metadata['specimen_from_organism.transplant_organ'] = sample_metadata.apply(lambda x: 'yes' if x['sample_source'] == 'organ_donor' else 'no', axis=1)
        conflict_1 = (sample_metadata['sample_source'] == 'postmortem donor') & (sample_metadata['manner_of_death'] == 'not applicable')
        conflict_2 = (sample_metadata['sample_source'] != 'postmortem donor') & (sample_metadata['manner_of_death'] != 'not applicable')
        if any(conflict_1) or any(conflict_2):
            print(f"Conflicting metadata {sample_metadata.loc[conflict_1, ['sample_source', 'manner_of_death']]}")
            print(f"Conflicting metadata {sample_metadata.loc[conflict_2, ['sample_source', 'manner_of_death']]}")
    return sample_metadata

def edit_hardy_scale(sample_metadata):
    hardy_scale = [0, 1, 2, 3, 4, '0', '1', '2', '3', '4']
    manner_of_death_is_living_dict = {n: 'no' for n in hardy_scale}
    manner_of_death_is_living_dict.update({'unknown': 'no', 'not applicable': 'yes'})

    if 'manner_of_death' in sample_metadata:
        sample_metadata['donor_organism.is_living'] = sample_metadata['manner_of_death'].replace(manner_of_death_is_living_dict)
        sample_metadata['donor_organism.death.hardy_scale'] = sample_metadata.apply(lambda x: x['manner_of_death'] if x['manner_of_death'] in hardy_scale else nan, axis=1)
    return sample_metadata

def sampled_site_to_known_diseases(row):
    if row['sampled_site_condition'] == 'adjacent' and 'disease_ontology_term_id' in row:
        if row['disease_ontology_term_id'] != 'PATO:0000461':
            print(f"Conflicting metadata {row[['sampled_site_condition', 'disease_ontology_term_id']]}")
        return ['PATO:0000461', row['disease_ontology_term_id']]
    elif row['sampled_site_condition'] in ['healthy', 'diseased'] and 'disease_ontology_term_id' in row:
        return [row['disease_ontology_term_id'], nan]
    elif row['sampled_site_condition'] == 'healthy':
        return ['PATO:0000461', nan]
    else:
        return [nan, nan]

def edit_sampled_site(sample_metadata):
    if 'sampled_site_condition' in sample_metadata:
        # if sampled_site_condition is adjacent, we fill adjacent_diseases with disease_ontology_term_id
        # if diseased: known_diseases = disease_ontology_term_id and adjacent = nan
        # if healthy: known_diseases = disease_ontology_term_id or PATO:0000461 and adjacent = nan

        sample_metadata[['specimen_from_organism.diseases.ontology', 'specimen_from_organism.adjacent_diseases.ontology']] = \
            sample_metadata.apply(sampled_site_to_known_diseases, axis=1, result_type='expand')
    return sample_metadata

def edit_alignment_software(sample_metadata):
    # we expect this to become an enum, when it would be easier to extract
    # for now we extract the numbers as in the example pattern
    if 'alignment_software' in sample_metadata:
        sample_metadata[['analysis_protocol.alignment_software', 'analysis_protocol.alignment_software_version']] = \
            sample_metadata['alignment_software'].str.extract(r'([\w\s]+)\s(v?[\d\.]+)')
        no_version = ~sample_metadata['alignment_software'].str.match(r'.*v?[\d\.]+')
        sample_metadata.loc[no_version, 'analysis_protocol.alignment_software'] = \
                sample_metadata.loc[no_version, 'alignment_software']
    return sample_metadata

def edit_cell_enrichment(sample_metadata):
    if 'cell_enrichment' in sample_metadata:
        # TODO keep + or - of enrichment and do only for not "na" values
        sample_metadata['cell_enrichment_cell_type'] = sample_metadata['cell_enrichment'].str[:-1]
        sample_metadata['enrichment_protocol.markers'] = sample_metadata['cell_enrichment_cell_type'].apply(ols_label)
        sample_metadata['cell_suspension.selected_cell_types.ontology'] = sample_metadata['cell_enrichment_cell_type']
        sample_metadata['cell_suspension.selected_cell_types.ontology_label'] = sample_metadata['cell_enrichment_cell_type'].apply(ols_label)
    return sample_metadata


def dev_label(ontology):
    start_id = ['start, days post fertilization', 'start, months post birth', 'start, years post birth']
    end_id = ['end, days post fertilization', 'end, months post birth', 'end, years post birth']
    print(f'Starting ontology {ontology}')
    result = ols_label(ontology, ontology= 'HsapDv', only_label=False)
    if not 'annotation' in result:
        print(f'Ontology {ontology} does not have annotation')
        return ontology
    start_key = [key for key in result['annotation'].keys() if key in start_id]
    if len(start_key) == 0:
        print(f'Ontology {ontology} does not have start annotation')
        return ontology
    elif len(start_key) > 1:
        print(f'Multiple start IDs {start_key}. Selecting the smallest value {start_key[0]}')
    unit_time = start_key[0].split(" ")[1].rstrip('s')
    age_range = [str(int(float(result['annotation'][start_key[0]][0])))]
    end_key = [key for key in result['annotation'].keys() if key in end_id]
    if len(end_key) == 0:
        return ' '.join([age_range[0],unit_time])
    result['annotation'][end_key[0]] = [str(int(float(result['annotation'][end_key[0]][0])) - 1)]
    age_range.extend(result['annotation'][end_key[0]])
    if float(age_range[1]) - float(age_range[0]) == 0:
        return ' '.join([age_range[0],unit_time])
    return ' '.join(['-'.join(age_range),unit_time])

def edit_dev_stage(sample_metadata):
    # local map of the most used ranges to reduce 
    dev_to_age_dict = {
        'HsapDv:0000264': '0-14 year',
        'HsapDv:0000268': '15-19 year',
        'HsapDv:0000237': '20-29 year',
        'HsapDv:0000238': '30-39 year',
        'HsapDv:0000239': '40-49 year',
        'HsapDv:0000240': '50-59 year',
        'HsapDv:0000241': '60-69 year',
        'HsapDv:0000242': '70-79 year',
        'HsapDv:0000243': '80-89 year'
    }

    if 'development_stage_ontology_term_id' in sample_metadata:
        sample_metadata[['donor_organism.organism_age', 'donor_organism.organism_age_unit.text']] = \
            sample_metadata['development_stage_ontology_term_id']\
                .apply(lambda x: dev_to_age_dict[x] if x in dev_to_age_dict.keys() else dev_label(x))\
                .str.split(' ', expand=True)
    return sample_metadata

def create_protocol_ids(dcp_spreadsheet, dcp_flat):
    protocols = [key.lower().replace(' ', '_') for key in dcp_spreadsheet if 'protocol' in key]

    for protocol in protocols:
        if dcp_flat.filter(like=protocol).empty:
            continue
        protocol_df = dcp_flat.filter(like=protocol).replace('na', nan).dropna().drop_duplicates()
        protocol_id_col = protocol + '.protocol_core.protocol_id'
        protocol_df[protocol_id_col] = [protocol + "_" + str(n + 1) for n in range(len(protocol_df))]
        dcp_flat = dcp_flat.merge(protocol_df,  how='left',on=list(protocol_df.columns.values[:-1]))
    return dcp_flat

def collapse_values(series):
    return "||".join(series.unique().astype(str))

def add_analysis_file(dcp_spreadsheet, collection_id, dataset_id):
    # We chould have 1 only Analysis file with all the CS merged
    dcp_spreadsheet['Analysis file']['analysis_file.file_core.file_name'] = f'{collection_id}_{dataset_id}.h5ad'
    dcp_spreadsheet['Analysis file']['analysis_file.file_core.content_description.text'] = 'count matrix'
    dcp_spreadsheet['Analysis file']['analysis_file.file_core.file_source'] = 'Contributor' # maybe add CxG
    dcp_spreadsheet['Analysis file']['analysis_file.file_core.format'] = 'h5ad'
    adata_protocol_ids = {
        'Library preparation protocol': 'library_preparation_protocol.protocol_core.protocol_id',
        'Sequencing protocol': 'sequencing_protocol.protocol_core.protocol_id',
        'Analysis protocol': 'analysis_protocol.protocol_core.protocol_id'
    }
    for tab, id in adata_protocol_ids.items():
        dcp_spreadsheet['Analysis file'][id] = \
        collapse_values(\
            dcp_spreadsheet[tab][id]
        )
    dcp_spreadsheet['Analysis file'] = dcp_spreadsheet['Analysis file']\
        .groupby('analysis_file.file_core.file_name')\
        .agg(collapse_values)\
        .reset_index()
    return dcp_spreadsheet

def export_to_excel(dcp_spreadsheet, collection_id, dataset_id):
    dcp_headers = get_dcp_headers()
    output_path = f"metadata/{collection_id}_{dataset_id}_dcp.xlsx"
    with pd.ExcelWriter(output_path) as writer:
        for tab_name, data in dcp_spreadsheet.items():
            if not data.empty:
                pd.concat([dcp_headers[tab_name], data], ignore_index=True).to_excel(writer, sheet_name=tab_name, index=False, header=False)

if __name__ == "__main__":
    args = define_parser().parse_args()
    collection_id = args.collection_id
    if args.dataset_id is not None:
        dataset_id = args.dataset_id
    else:
        dataset_ids = {file.split("_")[1] for file in os.listdir('metadata') if file.startswith(collection_id)}
        if len(dataset_ids) == 1:
            dataset_id = list(dataset_ids)[0]
        else:
            print("Please specify the dataset_id. There are available files for:")
            print('\n'.join(dataset_ids))
            sys.exit()

    try:
        sample_metadata_path = f"metadata/{collection_id}_{dataset_id}_metadata.csv"
        sample_metadata = pd.read_csv(sample_metadata_path)
    except FileNotFoundError:
        print(f"File not found: {sample_metadata_path}")

    study_metadata = read_study(collection_id, dataset_id)
    dcp_spreadsheet = get_dcp_spreadsheet()

    dcp_spreadsheet = add_doi(study_metadata, dcp_spreadsheet)
    dcp_spreadsheet = add_title(study_metadata, dcp_spreadsheet)
    dcp_spreadsheet = add_institute(sample_metadata, dcp_spreadsheet)

    sample_metadata = edit_collection_relative(sample_metadata)
    sample_metadata = edit_ncbitaxon(sample_metadata)
    sample_metadata = edit_sex(sample_metadata)
    sample_metadata = edit_sample_source(sample_metadata)
    sample_metadata = edit_hardy_scale(sample_metadata)
    sample_metadata = edit_sampled_site(sample_metadata)
    sample_metadata = edit_alignment_software(sample_metadata)
    # sample_metadata = edit_cell_enrichment(sample_metadata) # not yet functional
    sample_metadata = edit_dev_stage(sample_metadata)

    # Rename df columns
    dcp_flat = sample_metadata.rename(columns=tier1_to_dcp)
    dcp_flat = create_protocol_ids(dcp_spreadsheet, dcp_flat)

    # Generate spreadsheet
    for tab in dcp_spreadsheet:
        keys_union = [key for key in dcp_spreadsheet[tab].keys() if key in dcp_flat.keys()]
        # if entity of tab is not described in spreadsheet, skip tab
        if keys_union and (tab.lower().replace(" ", "_") not in [key.split('.')[0] for key in keys_union]):
            continue
        # collapse arrays in duplicated columns
        if any(dcp_flat[keys_union].columns.duplicated()):
            for dub_cols in set(dcp_flat[keys_union].columns[dcp_flat[keys_union].columns.duplicated()]):
                df = dcp_flat[dub_cols]
                dcp_flat.drop(columns=dub_cols, inplace=True)
                dcp_flat[dub_cols] = df[dub_cols].apply(lambda x: '||'.join(x.dropna().astype(str)),axis=1)

        # merge the two dataframes
        dcp_spreadsheet[tab] = pd.concat([dcp_spreadsheet[tab],dcp_flat[keys_union]])
        dcp_spreadsheet[tab] = dcp_spreadsheet[tab].dropna(how='all').drop_duplicates()

        if tab == 'Project':
            dcp_spreadsheet[tab] = dcp_spreadsheet[tab].drop_duplicates()
    dcp_spreadsheet = add_analysis_file(dcp_spreadsheet, collection_id, dataset_id)

    export_to_excel(dcp_spreadsheet, args.collection_id, args.dataset_id)


