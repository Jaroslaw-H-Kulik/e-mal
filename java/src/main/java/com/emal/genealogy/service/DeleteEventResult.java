package com.emal.genealogy.service;

/**
 * Mirrors delete_event's return shape (app/genealogy_repository.py): a
 * plain success/error result, never an exception for expected failures -
 * see AddPersonResult's javadoc for the same rationale.
 */
public sealed interface DeleteEventResult {

    record Success(boolean success, String eventId, int deletedParticipations, String message)
            implements DeleteEventResult {
        public Success(String eventId, int deletedParticipations, String message) {
            this(true, eventId, deletedParticipations, message);
        }
    }

    record Failure(boolean success, String error) implements DeleteEventResult {
        public Failure(String error) {
            this(false, error);
        }
    }
}
