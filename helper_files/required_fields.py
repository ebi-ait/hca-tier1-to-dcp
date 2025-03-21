from helper_files.tier1_mapping import entity_types

required_fields = {
    "project":
    [
        "project.project_core.project_short_name",
        "project.project_core.project_title",
        "project.project_core.project_description",
        "project.funders.grant_id",
        "project.funders.organization"

    ],
    "donor_organism":
    [
        "donor_organism.biomaterial_core.biomaterial_id",
        "donor_organism.biomaterial_core.ncbi_taxon_id",
        "donor_organism.sex",
        "donor_organism.is_living",
        "donor_organism.development_stage.text"
    ],
    "specimen_from_organism":
    [
        "specimen_from_organism.biomaterial_core.biomaterial_id",
        "specimen_from_organism.biomaterial_core.ncbi_taxon_id",
        "specimen_from_organism.organ.text"
    ],
    "cell_suspension":
    [
        "cell_suspension.biomaterial_core.biomaterial_id",
        "cell_suspension.biomaterial_core.ncbi_taxon_id"
    ],
    "cell_line":
    [
        "cell_line.biomaterial_core.biomaterial_id",
        "cell_line.biomaterial_core.ncbi_taxon_id",
        "cell_line.type.text",
        "cell_line.model_organ.text"
    ],
    "imaged_specimen":
    [
        "imaged_specimen.biomaterial_core.biomaterial_id",
        "imaged_specimen.biomaterial_core.ncbi_taxon_id",
        "imaged_specimen.slice_thickness"
    ],
    "organoid":
    [
        "organoid.biomaterial_core.biomaterial_id",
        "organoid.biomaterial_core.ncbi_taxon_id",
        "organoid.model_organ.text"
    ],
    "sequence_file":
    [
        "sequence_file.file_core.file_name",
        "sequence_file.file_core.format",
        "sequence_file.read_index"
    ],
    "analysis_file":
    [
        "analysis_file.file_core.file_name",
        "analysis_file.file_core.format",
        "analysis_file.genome_assembly_version"
    ],
    "image_files":
    [
        "image_files.file_core.file_name",
        "image_files.file_core.format"
    ],
    "supplementary_file":
    [
        "supplementary_file.file_core.file_name",
        "supplementary_file.file_core.format"
    ],
    "sequencing_protocol":
    [
        "sequencing_protocol.protocol_core.protocol_id",
        "sequencing_protocol.instrument_manufacturer_model.text",
        "sequencing_protocol.paired_end",
        "sequencing_protocol.method.text"
    ],
    "library_preparation_protocol":
    [
        "library_preparation_protocol.protocol_core.protocol_id",
        "library_preparation_protocol.input_nucleic_acid_molecule.text",
        "library_preparation_protocol.nucleic_acid_source",
        "library_preparation_protocol.library_construction_method.text",
        "library_preparation_protocol.end_bias",
        "library_preparation_protocol.strand"
    ],
    "analysis_protocol":
    [
        "analysis_protocol.protocol_core.protocol_id",
        "analysis_protocol.type.text"
    ],
    "aggregate_generation_protocol":
    [
        "aggregate_generation_protocol.protocol_core.protocol_id",
        "aggregate_generation_protocol.formation_method"
    ],
    "enrichment_protocol":
    [
        "enrichment_protocol.protocol_core.protocol_id",
        "enrichment_protocol.method.text"
    ],
    "dissociation_protocol":
    [
        "dissociation_protocol.protocol_core.protocol_id",
        "dissociation_protocol.method.text"
    ],
    "ipsc_induction_protocol":
    [
        "ipsc_induction_protocol.protocol_core.protocol_id",
        "ipsc_induction_protocol.method.text"
    ],
    "collection_protocol":
    [
        "collection_protocol.protocol_core.protocol_id",
        "collection_protocol.method.text"
    ],
    "differentiation_protocol":
    [
        "differentiation_protocol.protocol_core.protocol_id",
        "differentiation_protocol.method"
    ],
    "treatment_protocol":
    [
        "treatment_protocol.protocol_core.protocol_id",
        "treatment_protocol.method.text"
    ],
    "imaging_preparation_protocol":
    [
        "imaging_preparation_protocol.protocol_core.protocol_id"
    ],
    "imaging_protocol":
    [
        "imaging_protocol.protocol_core.protocol_id",
        "imaging_protocol.microscopy_technique.text",
        "imaging_protocol.magnification"
    ],
    "publications":
    [
        "project.publications.authors",
        "project.publications.title",
        "project.publications.official_hca_publication"
    ],
    "death":
    [
        "donor_organism.death.cause_of_death"
    ],
    "timecourse":
    [biomaterial.replace(" ", "_").lower() + '.biomaterial_core.' + timecourse for biomaterial in entity_types['biomaterial'] for timecourse in ['timecourse.value', 'timecourse.unit.text']],
    "barcode":
    [
        'library_preparation_protocol.cell_barcode.barcode_read', 
        'library_preparation_protocol.cell_barcode.barcode_offset', 
        'library_preparation_protocol.cell_barcode.barcode_length', 
        'library_preparation_protocol.umi_barcode.barcode_read', 
        'library_preparation_protocol.umi_barcode.barcode_offset', 
        'library_preparation_protocol.umi_barcode.barcode_length'
    ]
    # "channel":
    # [
    #     "channel.channel_id",
    #     "channel.excitation_wavelength",
    #     "channel.filter_range",
    #     "channel.multiplexed",
    #     "channel.exposure_time"
    # ],
    # "probe":
    # [
    #     "probe.probe_label",
    #     "probe.target_label",
    #     "probe.assay_type"
    # ],
    # "contributors":
    # [
    #     "contributors.name",
    #     "contributors.institution"
    # ],
    # "insdc_experiment_accession":
    # [
    #     "insdc_experiment_accession"
    # ],
    # "plate_based_sequencing":
    # [
    #     "plate_based_sequencing.plate_label"
    # ]
}
