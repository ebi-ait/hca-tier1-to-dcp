dcp_required_entities = {
    "Project": [
        "project.project_core.project_short_name",
        "project.project_core.project_title",
        "project.project_core.project_description",
        "project.funders"
    ],
    "Project - Contributors": [
        "project.contributors.name",
        "project.contributors.institution",
    ],
    "Project - Publications": [
        "project.publications.authors",
        "project.publications.title",
        "project.publications.official_hca_publication",
    ],
    "Project - Funders": [
        "project.funder.grant_id",
        "project.funder.organization",
    ],
    "Donor organism": [
        "donor_organism.biomaterial_core.biomaterial_id",
        "donor_organism.biomaterial_core.ncbi_taxon_id",
        "donor_organism.sex",
        "donor_organism.is_living",
        "donor_organism.development_stage",
    ],
    "Specimen from organism": [
        "specimen_from_organism.biomaterial_core.biomaterial_id",
        "specimen_from_organism.biomaterial_core.ncbi_taxon_id",
        "specimen_from_organism.organ",
    ],
    "Cell suspension": [
        "cell_suspension.biomaterial_core.biomaterial_id",
        "cell_suspension.biomaterial_core.ncbi_taxon_id",
    ],
    "Cell line": [
        "cell_line.biomaterial_core.biomaterial_id",
        "cell_line.biomaterial_core.ncbi_taxon_id",
        "cell_line.type",
        "cell_line.model_organ",
    ],
    "Imaged specimen": [
        "imaged_specimen.biomaterial_core.biomaterial_id",
        "imaged_specimen.biomaterial_core.ncbi_taxon_id",
        "imaged_specimen.slice_thickness",
    ],
    "Organoid": [
        "organoid.biomaterial_core.biomaterial_id",
        "organoid.biomaterial_core.ncbi_taxon_id",
        "organoid.model_organ",
    ],
    "Sequence file": [
        "sequence_file.file_core.file_name",
        "sequence_file.file_core.format",
        "sequence_file.read_index",
    ],
    "Analysis file": [
        "analysis_file.file_core.file_name",
        "analysis_file.file_core.format",
        "analysis_file.genome_assembly_version",
    ],
    "Image files": [
        "image_files.file_core.file_name",
        "image_files.file_core.format",
    ],
    "Supplementary file": [
        "supplementary_file.file_core.file_name",
        "supplementary_file.file_core.format",
    ],
    "Sequencing protocol": [
        "sequencing_protocol.protocol_core.protocol_id",
        "sequencing_protocol.instrument_manufacturer_model.text",
        "sequencing_protocol.paired_end",
        "sequencing_protocol.method",
    ],
    "Library preparation protocol": [
        "library_preparation_protocol.protocol_core.protocol_id",
        "library_preparation_protocol.input_nucleic_acid_molecule",
        "library_preparation_protocol.nucleic_acid_source",
        "library_preparation_protocol.library_construction_method",
        "library_preparation_protocol.end_bias",
        "library_preparation_protocol.strand",
    ],
    "Analysis protocol": [
        "analysis_protocol.protocol_core.protocol_id",
        "analysis_protocol.type",
    ],
    "Aggregate generation protocol": [
        "aggregate_generation_protocol.protocol_core.protocol_id",
        "aggregate_generation_protocol.formation_method",
    ],
    "Enrichment protocol": [
        "enrichment_protocol.protocol_core.protocol_id",
        "enrichment_protocol.method",
    ],
    "Dissociation protocol": [
        "dissociation_protocol.protocol_core.protocol_id",
        "dissociation_protocol.method",
    ],
    "Ipsc induction protocol": [
        "ipsc_induction_protocol.protocol_core.protocol_id",
        "ipsc_induction_protocol.method",
    ],
    "Collection protocol": [
        "collection_protocol.protocol_core.protocol_id",
        "collection_protocol.method",
    ],
    "Differentiation protocol": [
        "differentiation_protocol.protocol_core.protocol_id",
        "differentiation_protocol.method",
    ],
    "Treatment protocol": [
        "treatment_protocol.protocol_core.protocol_id",
        "treatment_protocol.method",
    ],
    "Imaging preparation protocol": [
        "imaging_preparation_protocol.protocol_core.protocol_id",
    ],
    "Imaging protocol": [
        "imaging_protocol.protocol_core.protocol_id",
        "imaging_protocol.microscopy_technique",
        "imaging_protocol.magnification",
    ]
}

dcp_required_modules = {
    "channel": [
        "channel.channel_id",
        "channel.excitation_wavelength",
        "channel.filter_range",
        "channel.multiplexed",
        "channel.exposure_time",
    ],
    "probe": [
        "probe.probe_label",
        "probe.target_label",
        "probe.assay_type",
    ],
    "death": [
        "death.cause_of_death",
    ],
    "timecourse": [
        "timecourse.value",
        "timecourse.unit",
    ],
    "barcode": [
        "barcode.barcode_read",
        "barcode.barcode_offset",
        "barcode.barcode_length",
    ],
    "plate_based_sequencing": [
        "plate_based_sequencing.plate_label",
    ]
}
