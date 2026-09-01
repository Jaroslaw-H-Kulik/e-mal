package com.emal.genealogy.service;

/** JSON body for POST /api/delete-document - see AddPersonRequest's javadoc for the DTO-over-Map rationale. */
public record DeleteDocumentRequest(String id) {
}
