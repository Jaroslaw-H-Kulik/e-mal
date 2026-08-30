package com.emal.genealogy.model;

import com.fasterxml.jackson.annotation.JsonAnyGetter;
import com.fasterxml.jackson.annotation.JsonAnySetter;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Field order matches data/genealogy_new_model.json exactly (see Person's
 * javadoc for why order matters here).
 */
public record EventParticipation(
        String id,
        String eventId,
        String personId,
        String role,
        @JsonAnyGetter @JsonAnySetter Map<String, Object> extra
) {
    public EventParticipation {
        if (extra == null) {
            extra = new LinkedHashMap<>();
        }
    }
}
