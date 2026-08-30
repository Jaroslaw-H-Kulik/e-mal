package com.emal.genealogy.model;

import com.fasterxml.jackson.annotation.JsonAnyGetter;
import com.fasterxml.jackson.annotation.JsonAnySetter;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Canonical field set established by the Phase 0 normalization
 * (JAVA_MIGRATION.md) - field order below matches
 * data/genealogy_new_model.json exactly so a no-op load/save round trip is
 * byte-identical.
 */
public record Person(
        String id,
        String firstName,
        String lastName,
        String gender,
        String maidenName,
        String occupation,
        List<String> tags,
        String notes,
        @JsonAnyGetter @JsonAnySetter Map<String, Object> extra
) {
    public Person {
        if (extra == null) {
            extra = new LinkedHashMap<>();
        }
    }
}
