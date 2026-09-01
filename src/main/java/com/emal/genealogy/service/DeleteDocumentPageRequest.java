package com.emal.genealogy.service;

/** JSON body for POST /api/delete-document-page - see AddPersonRequest's javadoc for the DTO-over-Map rationale. */
public record DeleteDocumentPageRequest(String docId, String filename) {
}
