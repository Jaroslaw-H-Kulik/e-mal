package com.emal.genealogy.service;

import java.util.List;

/**
 * Mirrors delete_person's return shape (app/genealogy_repository.py): a
 * plain success/error result, never an exception for expected failures -
 * see AddPersonResult's javadoc for the same rationale.
 */
public sealed interface DeletePersonResult {

    record Success(
            boolean success,
            int deletedParticipations,
            List<String> deletedEvents
    ) implements DeletePersonResult {
        public Success(int deletedParticipations, List<String> deletedEvents) {
            this(true, deletedParticipations, deletedEvents);
        }
    }

    record Failure(boolean success, String error) implements DeletePersonResult {
        public Failure(String error) {
            this(false, error);
        }
    }
}
