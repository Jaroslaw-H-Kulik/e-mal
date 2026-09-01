package com.emal.genealogy.service;

/** JSON body for POST /api/delete-person - see AddPersonRequest's javadoc for the DTO-over-Map rationale. */
public record DeletePersonRequest(String personId) {

    public DeletePersonRequest {
        personId = personId == null || personId.isEmpty() ? null : personId;
    }
}
