package com.emal.genealogy.service;

import com.emal.genealogy.model.Person;
import java.util.List;

/**
 * Mirrors update_person's return shape (app/genealogy_repository.py): a
 * plain success/error result, never an exception for expected failures -
 * see AddPersonResult's javadoc for the same rationale. "Person not found"
 * is the one real validation failure this endpoint has.
 */
public sealed interface UpdatePersonResult {

    record Success(boolean success, Person person, List<String> updatedEvents) implements UpdatePersonResult {
        public Success(Person person, List<String> updatedEvents) {
            this(true, person, updatedEvents);
        }
    }

    record Failure(boolean success, String error) implements UpdatePersonResult {
        public Failure(String error) {
            this(false, error);
        }
    }
}
