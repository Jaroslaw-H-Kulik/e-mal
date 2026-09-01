package com.emal.genealogy.service;

import java.util.List;

/** JSON body for POST /api/add-document, sent by document-manager.js's saveNewDocument. */
public record AddDocumentRequest(
        String name, Integer date, String notes, List<String> tags, String link,
        List<String> events, List<AddDocumentPageRequest> pages) {

    public AddDocumentRequest {
        name = name == null ? "" : name;
        notes = notes == null ? "" : notes;
        link = link == null ? "" : link;
        tags = tags == null ? List.of() : List.copyOf(tags);
        events = events == null ? List.of() : List.copyOf(events);
        pages = pages == null ? List.of() : List.copyOf(pages);
    }
}
