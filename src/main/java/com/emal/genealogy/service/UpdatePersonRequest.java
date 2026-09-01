package com.emal.genealogy.service;

import java.util.List;

/**
 * JSON body for POST /api/update-person, sent by editor.js's savePersonEdit -
 * see AddPersonRequest's javadoc for the DTO-over-Map rationale, and
 * PersonService's javadoc for why this endpoint moved from partial-update
 * (presence-based) to a plain PUT: the UI always sends every field now, so
 * there's no "was this key present" question left to answer.
 */
public record UpdatePersonRequest(
        String personId, String firstName, String lastName, String maidenName, String gender,
        String occupation, List<String> tags, String notes,
        DateRequest birthDate, String placeOfBirth, DateRequest deathDate, String placeOfDeath) {

    public UpdatePersonRequest {
        notes = notes == null || notes.isEmpty() ? null : notes;
        tags = tags == null ? List.of() : List.copyOf(tags);
    }
}
