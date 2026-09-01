package com.emal.genealogy.service;

/**
 * One entry of AddEventRequest/UpdateEventRequest's `participants` list -
 * see EventService.processParticipant/createParticipantPersonWithParents
 * for how each field is used.
 */
public record EventParticipantRequest(
        String existingPersonId, String role, String firstName, String lastName,
        Integer age, Integer calculatedBirthYear, String gender, String maidenName, String occupation,
        EventParentRequest parentMother, EventParentRequest parentFather) {
}
