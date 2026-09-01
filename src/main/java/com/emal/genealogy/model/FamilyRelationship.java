package com.emal.genealogy.model;

import com.fasterxml.jackson.annotation.JsonAnyGetter;
import com.fasterxml.jackson.annotation.JsonAnySetter;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Not currently persisted as its own top-level collection in
 * data/genealogy_new_model.json - relationships are derived at request time
 * from events/event_participations (see the add-relationship golden
 * fixtures). Kept here per JAVA_MIGRATION.md's documented model/ layout for
 * the step 5 (add-relationship) port.
 *
 * <p>person_1_id/person_2_id/source_event_id are spelled out explicitly
 * rather than left to the SNAKE_CASE naming strategy, since its digit-boundary
 * behavior on "person1Id" is ambiguous.
 */
public record FamilyRelationship(
        String id,
        @JsonProperty("person_1_id") String person1Id,
        @JsonProperty("person_2_id") String person2Id,
        String type,
        @JsonProperty("source_event_id") String sourceEventId,
        @JsonAnyGetter @JsonAnySetter Map<String, Object> extra
) {
    public FamilyRelationship {
        if (extra == null) {
            extra = new LinkedHashMap<>();
        }
    }
}
