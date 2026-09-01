package com.emal.genealogy.model;

import com.fasterxml.jackson.annotation.JsonAnyGetter;
import com.fasterxml.jackson.annotation.JsonAnySetter;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Field order matches data/genealogy_new_model.json exactly (see Person's
 * javadoc for why order matters here) - this is the CANONICAL_FIELDS order
 * from normalize_data_schema.py, which every event record's on-disk key
 * order was normalized to match (see JAVA_MIGRATION.md's Phase 0 addendum).
 */
public record Event(
        String id,
        String type,
        FlexibleDate date,
        String placeId,
        String content,
        String description,
        String title,
        String source,
        String notes,
        List<String> tags,
        List<String> links,
        @JsonAnyGetter @JsonAnySetter Map<String, Object> extra
) {
    public Event {
        if (extra == null) {
            extra = new LinkedHashMap<>();
        }
    }
}
