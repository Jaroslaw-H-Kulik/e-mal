package com.emal.genealogy.service;

import com.emal.genealogy.model.Document;

/**
 * Mirrors update_document's return shape (server.py): a plain
 * success/error result, never an exception for expected failures - see
 * AddPersonResult's javadoc for the same rationale.
 */
public sealed interface UpdateDocumentResult {

    record Success(boolean success, Document document) implements UpdateDocumentResult {
        public Success(Document document) {
            this(true, document);
        }
    }

    record Failure(boolean success, String error) implements UpdateDocumentResult {
        public Failure(String error) {
            this(false, error);
        }
    }
}
