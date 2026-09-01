package com.emal.genealogy.service;

import com.emal.genealogy.model.Event;
import com.emal.genealogy.model.EventParticipation;
import com.emal.genealogy.model.Person;
import java.util.Map;

/**
 * Mirrors add_person's return shape (app/genealogy_repository.py): a plain
 * success/error result, never an exception for expected failures - the
 * try/except in Python only guards against truly unexpected bugs, not real
 * validation (add_person has none). `success` is an explicit field on both
 * variants (not inferred from which record type it is) so it serializes
 * into the JSON response exactly like Python's dict does.
 */
public sealed interface AddPersonResult {

    record Success(
            boolean success,
            Person person,
            Map<String, Event> newEvents,
            Map<String, EventParticipation> newParticipations
    ) implements AddPersonResult {
        public Success(
                Person person,
                Map<String, Event> newEvents,
                Map<String, EventParticipation> newParticipations
        ) {
            this(true, person, newEvents, newParticipations);
        }
    }

    record Failure(boolean success, String error) implements AddPersonResult {
        public Failure(String error) {
            this(false, error);
        }
    }
}
