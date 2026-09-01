package com.emal.genealogy.service;

import java.util.List;

/**
 * JSON body for POST /api/add-person, sent by web/index.html's
 * add-person-form and editor.js's quick-add-from-relationship flow
 * (saveNewPersonAndRelationship) - see PersonService.addPerson. Field
 * names are snake_case on the wire (config/JacksonConfig maps
 * givenName -> given_name etc.). The only caller is this project's own
 * UI, so the compact constructor normalizes inputs to exactly what
 * those two call sites ever send: missing/blank strings collapse the
 * same way RequestValues' truthy()-based helpers used to on the raw
 * request map, and a missing tags array becomes an empty list.
 */
public record AddPersonRequest(
        String givenName,
        String surname,
        String gender,
        String maidenName,
        String occupation,
        List<String> tags,
        String notes,
        Integer birthYearEstimate,
        Integer deathYearEstimate,
        String placeOfBirth,
        String placeOfDeath) {

    public AddPersonRequest {
        givenName = givenName == null ? "" : givenName;
        surname = surname == null ? "" : surname;
        gender = gender == null ? "U" : gender;
        notes = blankToNull(notes);
        placeOfBirth = blankToNull(placeOfBirth);
        placeOfDeath = blankToNull(placeOfDeath);
        tags = tags == null ? List.of() : List.copyOf(tags);
    }

    private static String blankToNull(String value) {
        return value == null || value.isEmpty() ? null : value;
    }
}
