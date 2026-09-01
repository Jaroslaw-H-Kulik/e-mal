package com.emal.genealogy.service;

/**
 * Mirrors add_relationship's return shape (app/genealogy_repository.py): a
 * plain success/error result, never an exception for expected failures -
 * see AddPersonResult's javadoc for the same rationale. `createdEvent`/
 * `updatedEvent` are mutually exclusive (exactly one is non-null on
 * success) - whichever birth/marriage event the relationship type ended up
 * creating vs. reusing.
 */
public sealed interface AddRelationshipResult {

    record Success(boolean success, String createdEvent, String updatedEvent) implements AddRelationshipResult {
        public Success(String createdEvent, String updatedEvent) {
            this(true, createdEvent, updatedEvent);
        }
    }

    record Failure(boolean success, String error) implements AddRelationshipResult {
        public Failure(String error) {
            this(false, error);
        }
    }
}
