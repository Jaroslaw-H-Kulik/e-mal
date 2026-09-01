package com.emal.genealogy.service;

import com.emal.genealogy.model.Document;

/**
 * Mirrors delete_document_page's return shape (server.py): a plain
 * success/error result, never an exception for expected failures - see
 * AddPersonResult's javadoc for the same rationale.
 */
public sealed interface DeleteDocumentPageResult {

    record Success(boolean success, Document document) implements DeleteDocumentPageResult {
        public Success(Document document) {
            this(true, document);
        }
    }

    record Failure(boolean success, String error) implements DeleteDocumentPageResult {
        public Failure(String error) {
            this(false, error);
        }
    }
}
