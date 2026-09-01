package com.emal.genealogy.service;

/**
 * One entry of AddDocumentRequest's `pages` list - base64 image bytes to
 * write to disk plus a file extension. `data` is required (matches the old
 * RequestValues.requireString's Python-KeyError-shaped throw for a missing
 * page); `ext` defaults to "jpg" and is lowercased by DocumentService, same
 * as before.
 */
public record AddDocumentPageRequest(String data, String ext) {

    public AddDocumentPageRequest {
        ext = ext == null || ext.isEmpty() ? "jpg" : ext;
    }
}
