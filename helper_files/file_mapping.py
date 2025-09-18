FILE_MANIFEST_MAPPING = {
    "file_name": "sequence_file.file_core.file_name",
    "library_ID": "cell_suspension.biomaterial_core.biomaterial_id",
    "file_format": "sequence_file.file_core.format",
    "read_index": "sequence_file.read_index",
    "lane_index": "sequence_file.lane_index"
}

TIER_1_MAPPING = {
    "library_id": "cell_suspension.biomaterial_core.biomaterial_id",
    # "library_id_repository": "cell_suspension.biomaterial_core.biosamples_accession",
    "library_preparation_batch": "sequence_file.library_prep_id",
    "library_sequencing_run": "sequence_file.sequence_run_batch", 
    "assay_ontology_term_id": "library_preparation_protocol.library_construction_method.ontology", 
    "sequencing_platform": "sequencing_protocol.instrument_manufacturer_model.text"
}

FASTQ_STANDARD_FIELDS = {
    "sequence_file.file_core.content_description.text": "DNA sequence",
    "sequence_file.file_core.content_description.ontology": "EDAM:3494",
    "sequence_file.file_core.content_description.ontology_label": "DNA sequence"
}