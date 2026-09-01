package com.emal.genealogy.service;

import com.emal.genealogy.model.Event;
import com.emal.genealogy.model.Person;
import java.util.List;

/**
 * Mirrors add_event's return shape (app/genealogy_repository.py): a plain
 * success/error result, never an exception for expected failures - see
 * AddPersonResult's javadoc for the same rationale.
 */
public sealed interface AddEventResult {

    record Success(boolean success, Event event, List<Person> newPersons) implements AddEventResult {
        public Success(Event event, List<Person> newPersons) {
            this(true, event, newPersons);
        }
    }

    record Failure(boolean success, String error) implements AddEventResult {
        public Failure(String error) {
            this(false, error);
        }
    }
}
