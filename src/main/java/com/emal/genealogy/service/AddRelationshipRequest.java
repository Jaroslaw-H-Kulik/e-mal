package com.emal.genealogy.service;

/**
 * JSON body for POST /api/add-relationship, sent by editor.js's
 * createRelationship - see AddPersonRequest's javadoc for the DTO-over-Map
 * rationale. All 4 fields were genuinely required on the old raw-map
 * endpoint (Python KeyError semantics, see RelationshipService.addRelationship);
 * a `null` field here (JSON key omitted) is handled the same way there.
 */
public record AddRelationshipRequest(
        String basePersonId, String targetPersonId, String relationshipType, String role) {
}
