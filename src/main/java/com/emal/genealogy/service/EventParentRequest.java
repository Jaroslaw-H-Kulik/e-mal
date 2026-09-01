package com.emal.genealogy.service;

/**
 * A participant's inline `parent_mother`/`parent_father` object -
 * either an existing person by id, or a brand-new person's name (see
 * EventService.createParticipantPersonWithParents).
 */
public record EventParentRequest(String existingPersonId, String firstName, String lastName, String maidenName) {
}
