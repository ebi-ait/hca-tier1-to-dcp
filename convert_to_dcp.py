import argparse
import os
import re
import sys
import requests

import pandas as pd
from numpy import nan
from packaging.version import parse as parse_version

from helper_files.tier1_mapping import tier1_to_dcp, collection_dict, prot_def_field, tier1_enum, dev_to_age_dict, age_to_dev_dict
from helper_files.required_fields import required_fields


def define_parser():
    """Defines and returns the argument parser."""
    parser = argparse.ArgumentParser(description="Parser for the arguments")
    parser.add_argument("--collection_id", "-c", action="store",
                        dest="collection_id", type=str, required=True, help="Collection id")
    parser.add_argument("--dataset_id", "-d", action="store",
                        dest="dataset_id", type=str, required=False, help="Dataset id")
    parser.add_argument("--local_template", "-l", action="store",
                        dest="local_template", type=str, required=False, help="Local path of the HCA template")
    return parser

def get_dataset_id(collection_id, dataset_id=None):
    if dataset_id is not None:
        return dataset_id
    dataset_ids = [file.split("_")[1] for file in os.listdir('metadata') if file.startswith(collection_id)]
    if len(set(dataset_ids)) == 1:
        return dataset_ids[0]
    print("Please specify the -d dataset_id. There are available files for:")
    print('\n'.join(set(dataset_ids)))
    sys.exit()

def read_sample_metadata(collection_id, dataset_id):
    try:
        sample_metadata_path = f"metadata/{collection_id}_{dataset_id}_metadata.csv"
        print(f"Tier 1 obs spreadsheet found in {sample_metadata_path}")
        return pd.read_csv(sample_metadata_path)
    except FileNotFoundError:
        print(f"File not found: {sample_metadata_path}")
        return pd.DataFrame()
    except pd.errors.EmptyDataError:
        print(f"Empty file: {sample_metadata_path}")
        return pd.DataFrame()

def read_study_metadata(collection_id, dataset_id):
    try:
        metadata_path = f"metadata/{collection_id}_{dataset_id}_study_metadata.csv"
        metadata = pd.read_csv(metadata_path, header=None).T
        metadata.columns = metadata.iloc[0]
        print(f"Tier 1 uns spreadsheet found in {metadata_path}")
        return metadata.drop(0, axis=0)
    except FileNotFoundError:
        print(f"File not found: {metadata_path}")
        return pd.DataFrame()

def get_dcp_template(local_path=None):
    # if no internet connection, provide local path
    hca_template_url = 'https://github.com/ebi-ait/geo_to_hca/raw/master/template/hca_template.xlsx'
    path = local_path if local_path else hca_template_url
    try:
        return pd.read_excel(path, sheet_name=None, skiprows=[0, 1, 2, 4])
    except FileNotFoundError:
        print(f"Local file path not found: {local_path}")
        return {}
    except ConnectionError:
        print(f"Could not connect to {hca_template_url}. Please provide local_path instead.")
        return {}

def get_dcp_headers(local_path=None):
    # if no internet connection, provide local path
    hca_template_url = 'https://github.com/ebi-ait/geo_to_hca/raw/master/template/hca_template.xlsx'
    path = local_path if local_path else hca_template_url
    try:
        dcp_headers = pd.read_excel(path, sheet_name=None, header=None)
    except FileNotFoundError:
        print(f"Local file path not found: {path}")
        return {}
    except ConnectionError:
        print(f"Could not connect to {hca_template_url}. Use provide local_path instead.")
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
        titles = pd.DataFrame({'project.project_core.project_title': study_metadata['title']})
        dcp_spreadsheet['Project'] = pd.concat([dcp_spreadsheet['Project'], titles])
    return dcp_spreadsheet

def add_process_locations(sample_metadata, dcp_spreadsheet):
    if 'institute' in sample_metadata:
        dcp_spreadsheet['Cell suspension'] = process_site_type(sample_metadata, dcp_spreadsheet, 'institute')
    if 'sample_collection_site' in sample_metadata:
        dcp_spreadsheet['Specimen from organism'] = process_site_type(sample_metadata, dcp_spreadsheet, 'sample_collection_site')
    return dcp_spreadsheet

def tab_to_entity(tab):
    return tab.lower().replace(" ", "_")

def entity_to_tab(entity):
    return entity.capitalize().replace("_", " ")

def process_site_type(sample_metadata, dcp_spreadsheet, site_type):
    biomat_dcp = {'institute': 'Cell suspension',
                   'sample_collection_site': 'Specimen from organism'}
    biomat_tier1 = {'institute': 'library_id',
                   'sample_collection_site': 'sample_id'}
    return dcp_spreadsheet[biomat_dcp[site_type]].\
        merge(sample_metadata[[biomat_tier1[site_type], site_type]].drop_duplicates(), \
              how='left', right_on=biomat_tier1[site_type], \
              left_on=f'{tab_to_entity(biomat_dcp[site_type])}.biomaterial_core.biomaterial_id').\
        drop(columns=[biomat_tier1[site_type], 'process.process_core.location']).\
        rename(columns={site_type: 'process.process_core.location'})

# Get the ontology label instead of ontology id from OLS4
def ols_label(ontology_id, only_label=True, ontology=None):
    if ontology_id is nan:
        return ontology_id
    if re.match(r"\w+_\d+", ontology_id):
        ontology_id = ontology_id.replace("_", ":")
    if not re.match(r"\w+:\d+", ontology_id):
        return ontology_id
    ontology_name = ontology if ontology else ontology_id.split(":")[0].lower()
    ontology_term = ontology_id.replace(":", "_")
    url = f'https://www.ebi.ac.uk/ols4/api/ontologies/{ontology_name}/terms/http%253A%252F%252Fpurl.obolibrary.org%252Fobo%252F{ontology_term}'
    if ontology_name == 'efo':
        url = f'https://www.ebi.ac.uk/ols4/api/ontologies/{ontology_name}/terms/http%253A%252F%252Fwww.ebi.ac.uk%252Fefo%252F{ontology_term}'
    try:
        response = requests.get(url, timeout=100)
        results = response.json()
    except ConnectionError as e:
        print(e)
        return ontology_id
    return results['label'] if only_label else results

## Edit sample_metadata
def edit_collection_relative(sample_metadata):
    if 'sample_collection_relative_time_point' in sample_metadata:
        number_pattern = '([\\d]+[.|\\,]?\\d?)'
        if all(sample_metadata['sample_collection_relative_time_point'].apply(lambda x: isinstance(x, (bool, object)))):
            return sample_metadata
        sample_metadata['specimen_from_organism.biomaterial_core.timecourse.value'] = \
            sample_metadata['sample_collection_relative_time_point'].str.extract(number_pattern, expand=False)
        sample_metadata.loc[sample_metadata['sample_collection_relative_time_point'].notna(), 'specimen_from_organism.biomaterial_core.timecourse.relevance'] = 'relative time of collection'
        time_units_pattern = r'(hour|day|week|month|year)'
        sample_metadata['specimen_from_organism.biomaterial_core.timecourse.unit.text'] = \
            sample_metadata['sample_collection_relative_time_point'].str.extract(time_units_pattern, expand=False)
        print('`sample_collection_relative_time_point`', end='; ', flush=True)
    return sample_metadata

def collection_user_select(x):
    sample_id = x['sample_id']
    collection_method = x['sample_collection_method']
    tissue = ols_label(x['tissue_ontology_term_id'])
    death = x['manner_of_death']
    options = '\n'.join([str(i) + ': '+ term for i, term in enumerate(collection_dict[x['sample_collection_method']])])
    n = input(f"Please specify the collection method `{collection_method}` matching for sample {sample_id} " + \
        f"from {tissue} and manner of death {death}." + \
        f"Available options:\n{options}\n")
    if not n.isdigit() or int(n) not in range(len(collection_dict[x['sample_collection_method']])):
        raise TypeError(f"Please use a value from {list(range(len(collection_dict[x['sample_collection_method']])))}")
    return collection_dict[x['sample_collection_method']][int(n)]

def edit_collection_method(sample_metadata, collection_dict):
    if 'sample_collection_method' in sample_metadata:
        collect_fields = ['sample_collection_method', 'manner_of_death', 'tissue_ontology_term_id']
        sample_metadata['collection_protocol.method.text'] = sample_metadata\
        .apply(lambda x: x['sample_collection_method'] \
            if x['sample_collection_method'] not in collection_dict else None, axis=1)
        no_collect_comb = sample_metadata.loc[\
            sample_metadata['sample_collection_method'].isin(collection_dict), ['sample_id'] + collect_fields]\
            .drop_duplicates(subset=collect_fields)
        for _, row in no_collect_comb.iterrows():
            sample_metadata.loc[(sample_metadata[collect_fields] == row[collect_fields]).all(axis=1), 'collection_protocol.method.text'] = collection_user_select(row)
        print('`sample_collection_method`', end='; ', flush=True)
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
            for tissue_type in tissue_type_dcp:
                if tissue_type in sample_metadata['tissue_type'].values:
                    sample_metadata = tissue_type_taxon(sample_metadata, tissue_type, tissue_type_dcp)
        biomaterials = [col.split('.')[0] for col in sample_metadata if col.endswith("biomaterial_core.ncbi_taxon_id")]
        print(f'`ncbitaxon` for {", ".join(biomaterials)}', end='; ', flush=True)
    return sample_metadata

def edit_sex(sample_metadata):
    if 'sex_ontology_term_id' in sample_metadata:
        sample_metadata['donor_organism.sex'] = sample_metadata['sex_ontology_term_id'].apply(ols_label).fillna('unknown')
        allowed_sex_values = ['female', 'male', 'mixed', 'unknown']
        bool_sex_values = sample_metadata['donor_organism.sex'].isin(allowed_sex_values)
        if not bool_sex_values.all():
            unsupported_sex = sample_metadata.loc[~bool_sex_values, 'sex_ontology_term_id']
            print(f"Unsupported sex value {', '.join(unsupported_sex)}")
            return sample_metadata
        print('`sex`', end='; ', flush=True)
    return sample_metadata

def edit_ethnicity(sample_metadata):
    if 'self_reported_ethnicity_ontology_term_id' in sample_metadata:
        sample_metadata.loc[sample_metadata['self_reported_ethnicity_ontology_term_id'] == 'unknown', 'self_reported_ethnicity_ontology_term_id'] = nan
        if sample_metadata['self_reported_ethnicity_ontology_term_id'].isna().all():
            del sample_metadata['self_reported_ethnicity_ontology_term_id']
    print('`ethnicity`', end='; ', flush=True)
    return sample_metadata

def edit_sample_source(sample_metadata):
    if 'sample_source' in sample_metadata and 'manner_of_death' in sample_metadata:
        sample_metadata['specimen_from_organism.transplant_organ'] = sample_metadata.apply(lambda x: 'yes' if x['sample_source'] == 'organ_donor' else 'no', axis=1)
        conflict_1 = (sample_metadata['sample_source'] == 'postmortem donor') & (sample_metadata['manner_of_death'] == 'not applicable')
        conflict_2 = (sample_metadata['sample_source'] != 'postmortem donor') & (sample_metadata['manner_of_death'] != 'not applicable')
        if any(conflict_1) or any(conflict_2):
            print(f"Conflicting death metadata {sample_metadata.loc[conflict_1, ['sample_source', 'manner_of_death']]}")
            print(f"Conflicting death metadata {sample_metadata.loc[conflict_2, ['sample_source', 'manner_of_death']]}")
            return sample_metadata
        print('`sample_source`', end='; ', flush=True)
    return sample_metadata

def edit_hardy_scale(sample_metadata):
    hardy_scale = [0, 1, 2, 3, 4, '0', '1', '2', '3', '4']
    manner_of_death_is_living_dict = {n: 'no' for n in hardy_scale}
    manner_of_death_is_living_dict.update({'unknown': 'no', 'not applicable': 'yes'})
    
    if 'manner_of_death' in sample_metadata:
        sample_metadata['donor_organism.is_living'] = sample_metadata['manner_of_death'].replace(manner_of_death_is_living_dict)
        sample_metadata['donor_organism.death.hardy_scale'] = sample_metadata.apply(lambda x: x['manner_of_death'] if x['manner_of_death'] in hardy_scale else nan, axis=1)
        print('`hardy_scale`', end='; ', flush=True)
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
        if sample_metadata['specimen_from_organism.adjacent_diseases.ontology'].isna().all():
            del sample_metadata['specimen_from_organism.adjacent_diseases.ontology']
        print('`sampled_site`', end='; ', flush=True)
    return sample_metadata

def edit_alignment_software(sample_metadata):
    # we expect this to become an enum, when it would be easier to extract
    # for now we extract the numbers as in the example pattern
    if 'alignment_software' in sample_metadata:
        sample_metadata[['analysis_protocol.alignment_software', 'analysis_protocol.alignment_software_version']] = \
            sample_metadata['alignment_software'].str.extract(r'([\w\s]+)[\s\/](v?[\d\.]+\w?)')
        no_version = ~sample_metadata['alignment_software'].str.match(r'.*v?[\d\.]+')
        sample_metadata.loc[no_version, 'analysis_protocol.alignment_software'] = \
                sample_metadata.loc[no_version, 'alignment_software']
        # if alignment software is there, it's processed matrix generation
        sample_metadata['analysis_protocol.type.text'] = 'processed matrix generation'
        print('`alignment_software`', end='; ', flush=True)
    return sample_metadata

def edit_cell_enrichment(sample_metadata):
    if 'cell_enrichment' in sample_metadata:
        # TODO keep + or - of enrichment and do only for not "na" values
        if sample_metadata['cell_enrichment'] == "na":
            return 
        sample_metadata['cell_enrichment_cell_type'] = sample_metadata['cell_enrichment'].str[:-1]
        sample_metadata['enrichment_protocol.markers'] = sample_metadata['cell_enrichment_cell_type'].apply(ols_label)
        sample_metadata['cell_suspension.selected_cell_types.ontology'] = sample_metadata['cell_enrichment_cell_type']
        sample_metadata['cell_suspension.selected_cell_types.ontology_label'] = sample_metadata['cell_enrichment_cell_type'].apply(ols_label)
        print('`cell_enrichment`', end='; ', flush=True)
    return sample_metadata

def dev_label(ontology):
    start_id = ['start, days post fertilization', 'start, months post birth', 'start, years post birth']
    end_id = ['end, days post fertilization', 'end, months post birth', 'end, years post birth']
    result = ols_label(ontology, only_label=False)
    if not 'annotation' in result:
        print(f'Ontology {ontology} does not have annotation')
        return ontology
    start_key = [key for key in result['annotation'].keys() if key in start_id]
    if len(start_key) == 0:
        print(f'Ontology {ontology} does not have start annotation')
        return ontology
    elif len(start_key) > 1:
        print(f'\nMultiple start IDs {start_key}. Selecting the smallest value {start_key[0]}')
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
    if 'development_stage_ontology_term_id' in sample_metadata and sample_metadata['development_stage_ontology_term_id'].notna().any():
        sample_metadata[['donor_organism.organism_age', 'donor_organism.organism_age_unit.text']] = \
            sample_metadata['development_stage_ontology_term_id']\
                .apply(lambda x: dev_to_age_dict[x] if x in dev_to_age_dict else dev_label(x))\
                .str.split(' ', expand=True)
        print('`development_stage`', end='; ', flush=True)
    elif 'donor_organism.organism_age' in sample_metadata and sample_metadata['donor_organism.organism_age'].notna().any():
        sample_metadata[['donor_organism.organism_age', 'donor_organism.organism_age_unit.text']] = \
            sample_metadata['age']\
                .apply(lambda x: age_to_dev_dict[x] if x in age_to_dev_dict else nan)\
                .str.split(' ', expand=True)
        print('`donor_organism.organism_age`', end='; ', flush=True)
    return sample_metadata

def edit_lib_prep_protocol(sample_metadata):
    """If assay info is in CxG (either as label or ontology_id),
       and if assay is in cheatsheet
       add all lib_prep fields we have in cheatsheet"""
    cheatsheet = pd.read_csv('helper_files/lib_prep_cheatsheet.csv')
    field_map = {
        'assay_ontology_term_id': 'library_preparation_protocol.library_construction_method.ontology',
        'assay': 'library_preparation_protocol.library_construction_method.ontology_label'
        }
    if 'assay_ontology_term_id' in sample_metadata:
        assay_var = 'assay_ontology_term_id'
    elif 'assay' in sample_metadata:
        assay_var = 'assay'
    else:
        print("No `assay` or `assay_ontology_term_id` field found.")
        return sample_metadata
    if sample_metadata[assay_var].isin(cheatsheet[field_map[assay_var]]).any():
        print('`lib_prep fields`', end='; ', flush=True)
        assay_fields = cheatsheet.loc[cheatsheet[field_map[assay_var]].isin(sample_metadata[assay_var]),]\
            .dropna(axis=1)
        return sample_metadata.merge(assay_fields, how='left', 
                                     left_on=assay_var, right_on=field_map[assay_var])\
            .drop(field_map[assay_var], axis=1)
    return sample_metadata

def edit_suspension_type(sample_metadata):
    suspension_to_nucleic_acid = {'cell': 'single cell', 
                                  'nucleus': 'single nucleus',
                                  'na': 'bulk cell'}
    if 'suspension_type' in sample_metadata:
        sample_metadata['library_preparation_protocol.nucleic_acid_source'] = sample_metadata['suspension_type'].replace(suspension_to_nucleic_acid)
        if any(sample_metadata['suspension_type'] == 'na'):
            technologies = {ols_label(lib) for lib in sample_metadata.loc[sample_metadata['suspension_type'] == 'na', 'assay_ontology_term_id']}
            print("Please check if the following technologies use `bulk cell` and not single cell or nucleus:\n" + \
                  f"{'; '.join(technologies)}")
    return sample_metadata

def make_protocol_name(value: str):
    replacements = {
        ' ': '_',
        '/': '_',
        "'": "",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return value + "_protocol"

def create_protocol_ids(dcp_spreadsheet, dcp_flat):
    protocols = [tab_to_entity(key) for key in dcp_spreadsheet if 'protocol' in key]
    
    for protocol in protocols:
        if dcp_flat.filter(like=protocol).empty:
            continue
        protocol_df = dcp_flat.filter(like=protocol).replace('na', nan).dropna(axis=1).drop_duplicates()
        protocol_id_col = protocol + '.protocol_core.protocol_id'
        if protocol in prot_def_field and \
           prot_def_field[protocol] in protocol_df and \
           protocol_df[prot_def_field[protocol]].is_unique:
            protocol_df[protocol_id_col] = [make_protocol_name(value) for value in protocol_df[prot_def_field[protocol]].values]
        else:
            protocol_df[protocol_id_col] = [protocol + "_" + str(n + 1) for n in range(len(protocol_df))]
        dcp_flat = dcp_flat.merge(protocol_df,  how='left', on=list(protocol_df.columns.values[:-1]))
    return dcp_flat

def not_text(col, dcp_flat):
    return col.replace('ontology', 'text') not in dcp_flat

def not_label(col, dcp_flat):
    return col.replace('ontology', 'ontology_label') not in dcp_flat

def fill_ontology_labels(dcp_flat):
    ont_fields = [col for col in dcp_flat if col.endswith('ontology') and (not_text(col, dcp_flat) or not_label(col, dcp_flat))]
    for field in ont_fields:
        print(field, end='; ', flush=True)
        ont_dict = {value: ols_label(value) for value in dcp_flat[field].dropna().unique() if value}
        if not_text(field, dcp_flat):
            dcp_flat[field.replace("ontology","text")] = dcp_flat[field].replace(ont_dict)
        if not_label(field, dcp_flat):
            dcp_flat[field.replace("ontology","ontology_label")] = dcp_flat[field].replace(ont_dict)
    print('\t')
    return dcp_flat

def get_xml_keys(schemas_url="https://schema.humancellatlas.org/"):
    response = requests.get(schemas_url, timeout=10)
    return [key.split('</Key>')[0] for key in response.text.split('<Key>')]

def get_entity_schema(entity, xml_keys, schemas_url="https://schema.humancellatlas.org/"):
    entity_keys = [key for key in xml_keys if key.split('/')[-1] == entity]
    if not entity_keys:
        return {}
    entity_key_versions = [parse_version(key.split('/')[-2]) for key in entity_keys]
    # use the latest version
    key = entity_keys[entity_key_versions.index(max(entity_key_versions))]
    response = requests.get(schemas_url + key, timeout=10)
    return response.json()

def get_enum_restriction(field, xml_keys, schemas_url="https://schema.humancellatlas.org/"):
    key_schema = {}
    if field.split('.')[-1] in ['text', 'ontology', 'ontology_label']:
        field = '.'.join(field.split('.')[:-1])
    prop = field.split('.')[-1]
    key = field.split('.')[-2]
    key_schema = get_entity_schema(key, xml_keys, schemas_url)
    if key_schema and 'enum' in key_schema['properties'][prop]:
        return key_schema['properties'][prop]['enum']
    print(f'Could not retrieve enum restriction for {field}')

def get_ontology_restriction(field, xml_keys, schemas_url="https://schema.humancellatlas.org/"):
    key_schema = {}
    if field.split('.')[-1] not in ['text', 'ontology', 'ontology_label']:
        print(f'Field {field} is not an ontology field.')
        return
    ont_prop = field.split('.')[-2]
    key = field.split('.')[-3]
    key_schema = get_entity_schema(key, xml_keys, schemas_url)
    if not key_schema:
        prop = field.split('.')[-3]
        prev_key = field.split('.')[-4]
        prev_key_schema = get_entity_schema(prev_key, xml_keys, schemas_url)['properties'][prop]
        if '$ref' in prev_key_schema:
            key_schema = requests.get(prev_key_schema['$ref'], timeout=10).json()
        elif 'items' in prev_key_schema and '$ref' in prev_key_schema['items']:
            key_schema = requests.get(prev_key_schema['items']['$ref'], timeout=10).json()
    prop_schema = key_schema['properties'][ont_prop]
    
    if not key_schema and not prop_schema:
        print(f'Could not retrieve ontology restriction for {field}')
        return
    if '$ref' in prop_schema:
        ontology_response = requests.get(prop_schema['$ref'], timeout=10)
    elif 'items' in prop_schema and '$ref' in prop_schema['items']:
        ontology_response = requests.get(prop_schema['items']['$ref'], timeout=10)
    else:
        print(f'No ontology link found in {key_schema}')
        return
    if 'ontology' in ontology_response.json()['properties']:
        return [ont.replace('obo:','') for ont in ontology_response.json()['properties']['ontology']['graph_restriction']['ontologies']]
    return

def fill_ontology_ids(term, field, xml_keys, silent=False):
    ontologies = get_ontology_restriction(field, xml_keys)
    if not ontologies:
        return term
    for ontology in ontologies:
        request_query = 'https://www.ebi.ac.uk/ols4/api/search?q='
        response = requests.get(request_query + f"{term.replace(' ', '+')}&ontology={ontology}", timeout=10).json()
        if response["response"]["numFound"] == 0:
            print(f"No ontology found for {term} in {ontology}")
            continue
        label = response["response"]["docs"][0]['label']
        obo_id = response["response"]["docs"][0]['obo_id']
        if not silent:
            print(f"Selecting {label}/{obo_id} for {term}")
        return obo_id

def fill_missing_ontology_ids(dcp_flat):
    fields = [x for x in dcp_flat if x.endswith('text') and x.replace('text','ontology') not in dcp_flat]
    xml_keys = get_xml_keys()
    for field in fields:
        print(field, end='; ', flush=True)
        ont_dict = {value: fill_ontology_ids(value, field, xml_keys, silent=True) for value in dcp_flat[field].unique() if value}
        dcp_flat[field.replace('text','ontology')] = dcp_flat[field].replace(ont_dict)
    return dcp_flat

def check_enum_values(dcp_flat):
    xml_keys = get_xml_keys()
    for field in tier1_enum:
        if field in dcp_flat:
            enum = get_enum_restriction(field, xml_keys)
            not_in_enum = [value for value in dcp_flat[field].unique() if value not in enum and value is not nan]
            if not_in_enum:
                print(f"{BOLD_START}WARNING:{BOLD_END}\n\tValue(s) `{', '.join(not_in_enum)}` are not valid in {field} schema", end='')

def populate_spreadsheet(dcp_spreadsheet, dcp_flat):
    for tab in dcp_spreadsheet:
        keys_union = [key for key in dcp_spreadsheet[tab].keys() if key in dcp_flat.keys()]
        # if entity of tab is not described in spreadsheet, skip tab
        keys_union_tabs = [key.split('.')[0].capitalize().replace("_", " ") for key in keys_union]
        if not keys_union or (tab not in keys_union_tabs):
            continue
        # collapse arrays in duplicated columns
        if any(dcp_flat[keys_union].columns.duplicated()):
            for dub_cols in set(dcp_flat[keys_union].columns[dcp_flat[keys_union].columns.duplicated()]):
                df = dcp_flat[dub_cols]
                dcp_flat.drop(columns=dub_cols, inplace=True)
                dcp_flat[dub_cols] = df[dub_cols].apply(lambda x: '||'.join(x.dropna().astype(str)),axis=1)
        # copy dtypes in dcp_spreadsheet
        dcp_spreadsheet[tab] = dcp_spreadsheet[tab].astype(dcp_flat[keys_union].dtypes.to_dict())
        # merge the two dataframes
        dcp_spreadsheet[tab] = pd.concat([dcp_spreadsheet[tab],dcp_flat[keys_union]])
        dcp_spreadsheet[tab] = dcp_spreadsheet[tab].dropna(how='all').drop_duplicates()
        if tab == 'Project':
            dcp_spreadsheet[tab] = dcp_spreadsheet[tab].drop_duplicates()
    return dcp_spreadsheet

def collapse_values(series):
    return "||".join(series.unique().astype(str))

def add_analysis_file(dcp_spreadsheet, collection_id, dataset_id):
    # We chould have 1 only Analysis file with all the CS merged
    analysis_file_metadata = {
        'analysis_file.file_core.file_name': f'{collection_id}_{dataset_id}.h5ad',
        'analysis_file.file_core.content_description.text': 'Count matrix',
        'analysis_file.file_core.content_description.ontology': 'EDAM:3917',
        'analysis_file.file_core.content_description.ontology_label': 'Count matrix',
        'analysis_file.file_core.file_source': 'Contributor',
        'analysis_file.file_core.format': 'h5ad'
        }
    
    for key in dcp_spreadsheet['Analysis file']:
        if key in analysis_file_metadata:
            dcp_spreadsheet['Analysis file'][key] = analysis_file_metadata[key]
    
    dcp_spreadsheet['Analysis file'] = dcp_spreadsheet['Analysis file']\
        .groupby('analysis_file.file_core.file_name')\
        .agg(collapse_values)\
        .reset_index()
    print('Added `Analysis file` info')
    return dcp_spreadsheet

def check_required_fields(dcp_spreadsheet):
    all_fields = []
    missing_required = set()
    missing_dict = {}
    for tab in dcp_spreadsheet:
        if dcp_spreadsheet[tab].empty:
            continue
        all_fields.extend(dcp_spreadsheet[tab].dropna(axis=1, how='all').columns.tolist())
    for field in all_fields:
        # req_modules = [key for key in required_fields if field.startswith(key)]
        modules = [key for key in required_fields if key in field]
        for module in modules:
            missing_required.update([req_field for req_field in required_fields[module] if req_field not in all_fields])
    for field in missing_required:
        key = entity_to_tab(field.split('.')[0])
        if key not in missing_dict:
            missing_dict[key] = [field]
        else:
            missing_dict[key].append(field)
    print(f"{BOLD_START}MISSING DCP REQUIRED FIELDS: {BOLD_END}")
    for key, values in missing_dict.items():
        print(f"\t{key}:\t{', '.join(values)}")

def export_to_excel(dcp_spreadsheet, collection_id, dataset_id, local_template):
    dcp_headers = get_dcp_headers(local_template)
    output_path = f"metadata/{collection_id}_{dataset_id}_dcp.xlsx"
    with pd.ExcelWriter(output_path) as writer:
        for tab_name, data in dcp_spreadsheet.items():
            if not data.empty:
                pd.concat([dcp_headers[tab_name], data], ignore_index=True).to_excel(writer, sheet_name=tab_name, index=False, header=False)
    print(f'Exported to {output_path}')

def main(collection_id, dataset_id=None, local_template=None):
    dataset_id = get_dataset_id(collection_id, dataset_id)
    print(f"{BOLD_START}READING FILES{BOLD_END}")
    sample_metadata = read_sample_metadata(collection_id, dataset_id)
    study_metadata = read_study_metadata(collection_id, dataset_id)
    
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
    dcp_spreadsheet = add_analysis_file(dcp_spreadsheet, collection_id, dataset_id)
    check_required_fields(dcp_spreadsheet)

    print(f"{BOLD_START}EXPORTING SPREADSHEET{BOLD_END}")
    export_to_excel(dcp_spreadsheet, collection_id, dataset_id, local_template)

BOLD_START = '\033[1m'
BOLD_END = '\033[0;0m'

if __name__ == "__main__":
    args = define_parser().parse_args()
    main(collection_id=args.collection_id, dataset_id=args.dataset_id, local_template=args.local_template)
