package com.emal.genealogy.service;

/**
 * One entry of UpdateDocumentRequest's `pages` list - an existing page's
 * filename plus its (possibly edited) transcription text. Distinct shape
 * from AddDocumentPageRequest: no `data`/`ext`, since update-document never
 * writes files (only add-document/delete-document-page do).
 */
public record UpdateDocumentPageRequest(String filename, String transcription) {
}
