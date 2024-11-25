"""
Dictionary with keys Tier 1 fields, and values, the corresponding DCP fields
Fields that are conditionally changed are not part of the dictionary to avoid duplications
"""

tier1_to_dcp = {
    'title': 'project.project_core.project_title',
    'study_pi': 'project.contributors.name',
    # batch_condition
    # default_embedding
    # comments
    'sample_id': 'specimen_from_organism.biomaterial_core.biomaterial_id',
    'donor_id': 'donor_organism.biomaterial_core.biomaterial_id',
    'protocol_url': 'library_preparation_protocol.protocol_core.protocols_io_doi',
    # 'institute': 'project.contributors.institute',
    # 'sample_collection_site': 'sample_collection_site',
    # 'sample_collection_relative_time_point': 'specimen_from_organism.biomaterial_core.timecourse.value',
    'library_id': 'cell_suspension.biomaterial_core.biomaterial_id',
    'library_id_repository': 'cell_suspension.biomaterial_core.biomaterial_name',
    # 'author_batch_notes': 'cell_suspension.biomaterial_core.biomaterial_description',
    # 'organism_ontology_term_id': 'donor_organism.biomaterial_core.ncbi_taxon_id',
    # 'manner_of_death': 'donor_organism.death.hardy_scale',
    # 'sample_source': 'donor_organism.is_living',
    # 'sex_ontology_term_id': 'donor_organism.sex',
    'sample_collection_method': 'collection_protocol.method.text',
    # tissue_type
    # 'sampled_site_condition': 'specimen_from_organism.diseases.text', # if is healthy PATO, if adjacent PATO & adjacent disease_ontology_term_id, else disease_ontology_term_id
    'tissue_ontology_term_id': 'specimen_from_organism.organ.ontology',
    'tissue_free_text': 'specimen_from_organism.organ_parts.text',
    'sample_preservation_method': 'specimen_from_organism.preservation_storage.storage_method',
    # 'suspension_type': 'library_preparation_protocol.nucleic_acid_source',
    # 'cell_enrichment': 'enrichment_protocol.markers', # if CL ontology add CL label
    'cell_viability_percentage': 'cell_suspension.cell_morphology.percent_cell_viability',
    'cell_number_loaded': 'cell_suspension.estimated_cell_count',
    'sample_collection_year': 'specimen_from_organism.collection_time',
    'assay_ontology_term_id': 'library_preparation_protocol.library_construction_method.ontology',
    'library_preparation_batch': 'sequence_file.library_prep_id',
    'library_sequencing_run': 'sequence_file.sequencing_run_batch',
    'sequenced_fragment': 'library_preparation_protocol.end_bias',
    'sequencing_platform': 'sequencing_protocol.instrument_manufacturer_model.ontology',
    # is_primary_data
    'reference_genome': 'analysis_file.genome_assembly_version',
    'gene_annotation_version': 'analysis_protocol.gene_annotation_version',
    # 'alignment_software': 'analysis_protocol.alignment_software',
    'intron_inclusion': 'analysis_protocol.intron_inclusion',
    # author_cell_type
    # cell_type_ontology_term_id
    'disease_ontology_term_id': 'donor_organism.diseases.ontology',
    'self_reported_ethnicity_ontology_term_id': 'donor_organism.human_specific.ethnicity.ontology',
    'development_stage_ontology_term_id': 'donor_organism.development_stage.ontology'
}

tier1 = {'uns': {
        'MUST':
            ['title', 'study_pi'],
        'RECOMMENDED':
            ['batch_condition', 'default_embedding', 'comments']
    },
    'obs': {
        'MUST':
            ['sample_id', 'donor_id', 'institute', 'library_id', 'organism_ontology_term_id',
            'manner_of_death', 'sample_source', 'sex_ontology_term_id', 'sample_collection_method',
            'tissue_type', 'sampled_site_condition', 'tissue_ontology_term_id',
            'sample_preservation_method', 'suspension_type',
            'cell_enrichment', 'assay_ontology_term_id', 'library_preparation_batch',
            'library_sequencing_run', 'sequenced_fragment',
            'is_primary_data', 'reference_genome', 
            'gene_annotation_version', 'alignment_software', 
            'author_cell_type', 'cell_type_ontology_term_id', 
            'disease_ontology_term_id',
            'self_reported_ethnicity_ontology_term_id', 'development_stage_ontology_term_id'],
        'RECOMMENDED':
            ['protocol_url', 'sample_collection_site', 'sample_collection_relative_time_point',
            'library_id_repository', 'author_batch_notes', 'tissue_free_text',
            'cell_viability_percentage', 'cell_number_loaded', 'sample_collection_year',
            'sequencing_platform', 'intron_inclusion']
    }
}
tier1_list = ['title', 'study_pi', 
              'batch_condition', 'default_embedding', 'comments', 
              'sample_id', 'donor_id', 'protocol_url', 'institute', 
              'sample_collection_site', 'sample_collection_relative_time_point', 
              'library_id', 'library_id_repository', 'author_batch_notes', 
              'organism_ontology_term_id', 'manner_of_death', 'sample_source', 
              'sex_ontology_term_id', 'sample_collection_method', 'tissue_type', 
              'sampled_site_condition', 'tissue_ontology_term_id', 
              'tissue_free_text', 'sample_preservation_method', 
              'suspension_type', 'cell_enrichment', 
              'cell_viability_percentage', 'cell_number_loaded', 
              'sample_collection_year', 'assay_ontology_term_id', 
              'library_preparation_batch', 'library_sequencing_run', 
              'sequenced_fragment', 'sequencing_platform', 'is_primary_data', 
              'reference_genome', 'gene_annotation_version', 
              'alignment_software', 'intron_inclusion', 
            #   'author_cell_type', 'cell_type_ontology_term_id', 
              'disease_ontology_term_id', 
              'self_reported_ethnicity_ontology_term_id', 
              'development_stage_ontology_term_id']
"""
Dictionary with protocol name defining fields to generate a context meaningfull protocol namelike i.e. 10x_3_v2_protocol, biopsy_protocol etc.
"""
prot_def_field = {
    'collection_protocol': 'collection_protocol.method.text',
    'library_preparation_protocol': 'library_preparation_protocol.library_construction_method.text', 
    'sequencing_protocol': 'sequencing_protocol.instrument_manufacturer_model.text',
    'analysis_protocol': 'analysis_protocol.alignment_software',
    'enrichment_protocol': 'enrichment_protocol.markers',
}


entity_types = {
    "project":
    [
        "Project",
        "Project - Contributors",
        "Project - Publications",
        "Project - Funders"
    ],
    "biomaterial":
    [
        "Donor organism",
        "Specimen from organism",
        "Cell suspension",
        "Organoid",
        "Imaged specimen",
        "Cell line"
    ],
    "file":
    [
        "Supplementary file",
        "Sequence file",
        "Analysis file",
        "Image file"
    ],
    "protocol":
    [
        "Collection protocol",
        "Treatment protocol",
        "Dissociation protocol",
        "Differentiation protocol",
        "Enrichment protocol",
        "Aggregate generation protocol",
        "Ipsc induction protocol",
        "Imaging preparation protocol",
        "Imaging protocol",
        "Library preparation protocol",
        "Sequencing protocol",
        "Analysis protocol",
        "Additional reagents",
        "Imaging protocol - Channel",
        "Imaging protocol - Probe"
    ],
    "module":
    [
        "Familial relationship",
        "Project - hca bionetworks"
    ]
}

all_entities = [
    "Project",
    "Project - Contributors",
    "Project - Publications",
    "Project - Funders",
    "Donor organism",
    "Specimen from organism",
    "Cell suspension",
    "Organoid",
    "Imaged specimen",
    "Cell line"
    "Supplementary file",
    "Sequence file",
    "Analysis file",
    "Image file",
    "Collection protocol",
    "Treatment protocol",
    "Dissociation protocol",
    "Differentiation protocol",
    "Enrichment protocol",
    "Aggregate generation protocol",
    "Ipsc induction protocol",
    "Imaging preparation protocol",
    "Imaging protocol",
    "Library preparation protocol",
    "Sequencing protocol",
    "Analysis protocol",
    "Additional reagents",
    "Imaging protocol - Channel",
    "Imaging protocol - Probe",
    "Familial relationship",
    "Project - hca bionetworks"
]

collection_dict = {"brush": ['EFO:0010741', 'EFO:0011029'],
                   "scraping": 'EFO:0009122',
                   "biopsy": 'EFO:0009120',
                   "surgical resection": 'EFO:0009744',
                   "blood draw": 'EFO:0009121',
                   "body fluid": ['EFO:0030020', 'EFO:0009123', 'EFO:0700013', 
                                  'OBI:0600044', 'EFO:0010960', 'EFO:0030079'],
                   "other": ['EFO:0009292', 'EFO:0009627', 'EFO:0010728', 'EFO:0003856', 
                             'EFO:0009807', 'EFO:0009808', 'EFO:0010173', 'EFO:0009124', 
                             'EFO:0010174', 'EFO:0700009', 'EFO:0010727']}
