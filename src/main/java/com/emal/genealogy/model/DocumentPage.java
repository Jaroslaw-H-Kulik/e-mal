package com.emal.genealogy.model;

import com.fasterxml.jackson.annotation.JsonAnyGetter;
import com.fasterxml.jackson.annotation.JsonAnySetter;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * One scanned page of a Document. Field order/shape matches every real
 * data/documents.json page entry exactly - checked directly against the
 * live file (133 pages across 14 documents): all of them already share
 * this exact 2-key set/order, so unlike genealogy_new_model.json, no
 * Phase-0-style normalization pass was needed before this could be a
 * plain record (see JAVA_MIGRATION.md's "Document management port"
 * section).
 */
public record DocumentPage(
        String filename,
        String transcription,
        @JsonAnyGetter @JsonAnySetter Map<String, Object> extra
) {
    public DocumentPage {
        if (extra == null) {
            extra = new LinkedHashMap<>();
        }
    }
}
