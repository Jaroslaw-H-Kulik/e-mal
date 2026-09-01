package com.emal.genealogy.model;

import java.util.Map;

/**
 * Root shape of data/genealogy_new_model.json. "metadata" is kept as a raw
 * Map (not a typed record) deliberately: it's not written by any service
 * logic yet, and typing its last_updated timestamp risks Jackson
 * reformatting it on save (precision/offset differences) and breaking the
 * byte-identical round-trip exit criterion for step 1.
 */
public record GenealogyDocument(
        Map<String, Person> persons,
        Map<String, Place> places,
        Map<String, Event> events,
        Map<String, EventParticipation> eventParticipations,
        Map<String, Object> metadata
) {
}
