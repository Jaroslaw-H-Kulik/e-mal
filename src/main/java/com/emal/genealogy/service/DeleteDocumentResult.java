package com.emal.genealogy.service;

/**
 * Mirrors delete_document's return shape (server.py): success carries no
 * payload beyond the flag ({@code {'success': True}}, no "document" key -
 * unlike delete_document_page, which returns the surviving document). See
 * AddPersonResult's javadoc for why failures are a plain result, not an
 * exception.
 */
public sealed interface DeleteDocumentResult {

    record Success(boolean success) implements DeleteDocumentResult {
        public Success() {
            this(true);
        }
    }

    record Failure(boolean success, String error) implements DeleteDocumentResult {
        public Failure(String error) {
            this(false, error);
        }
    }
}
