package com.emal.genealogy.service;

/** JSON body for POST /api/delete-event - see AddPersonRequest's javadoc for the DTO-over-Map rationale. */
public record DeleteEventRequest(String eventId) {

    public DeleteEventRequest {
        eventId = eventId == null || eventId.isEmpty() ? null : eventId;
    }
}
