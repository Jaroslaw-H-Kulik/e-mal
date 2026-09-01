package com.emal.genealogy.model;

import com.fasterxml.jackson.annotation.JsonAnyGetter;
import com.fasterxml.jackson.annotation.JsonAnySetter;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * A scanned archival document (data/documents.json - a flat {@code
 * {doc_id: document}} map, entirely separate from
 * genealogy_new_model.json/GenealogyRepository). Field order matches every
 * real row exactly - checked directly against the live file (all 14 rows
 * already share this identical 8-key set/order, unlike
 * genealogy_new_model.json before Phase 0 - see JAVA_MIGRATION.md's
 * "Document management port" section).
 *
 * <p>{@code date} is a plain nullable year ({@link Integer}), NOT a
 * {@link FlexibleDate} like {@code Event.date} - confirmed against the
 * live file (13 int years, 1 null, zero FlexibleDate-shaped objects).
 */
public record Document(
        String id,
        String name,
        Integer date,
        String notes,
        List<String> tags,
        String link,
        List<String> events,
        List<DocumentPage> pages,
        @JsonAnyGetter @JsonAnySetter Map<String, Object> extra
) {
    public Document {
        if (extra == null) {
            extra = new LinkedHashMap<>();
        }
    }
}
