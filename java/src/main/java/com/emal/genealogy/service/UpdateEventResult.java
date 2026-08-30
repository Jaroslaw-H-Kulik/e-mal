package com.emal.genealogy.service;

import com.emal.genealogy.model.Event;
import com.emal.genealogy.model.EventParticipation;
import com.emal.genealogy.model.Person;
import java.util.List;
import java.util.Map;

/**
 * Mirrors update_event's return shape (app/genealogy_repository.py): a plain
 * success/error result, never an exception for expected failures - see
 * AddPersonResult's javadoc for the same rationale. Unlike AddEventResult,
 * the success response also carries the event's now-current
 * event_participations map (update_event fully replaces the participant
 * list, so the client needs it to patch in-memory) and any existing
 * participants whose maiden_name was modified in place.
 */
public sealed interface UpdateEventResult {

    record Success(
            boolean success,
            Event event,
            Map<String, EventParticipation> eventParticipations,
            List<Person> newPersons,
            List<Person> modifiedPersons,
            String message
    ) implements UpdateEventResult {
        public Success(
                Event event,
                Map<String, EventParticipation> eventParticipations,
                List<Person> newPersons,
                List<Person> modifiedPersons,
                String message
        ) {
            this(true, event, eventParticipations, newPersons, modifiedPersons, message);
        }
    }

    record Failure(boolean success, String error) implements UpdateEventResult {
        public Failure(String error) {
            this(false, error);
        }
    }
}
