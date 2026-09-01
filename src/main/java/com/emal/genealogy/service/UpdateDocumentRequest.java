package com.emal.genealogy.service;

import java.util.List;

/**
 * JSON body for POST /api/update-document, sent by document-manager.js's
 * saveEditDocument/linkDocumentToEvent/unlinkDocumentFromEvent - all three
 * call sites always send the complete field set (the latter two by
 * spreading the existing document object), so this always-overwrites every
 * field rather than replicating the old per-key `containsKey` partial-update
 * (see AddPersonRequest's javadoc for the general DTO-over-Map rationale;
 * this is a deliberate behavior simplification, not preserved by any test -
 * see JAVA_MIGRATION.md/PR notes).
 */
public record UpdateDocumentRequest(
        String id, String name, Integer date, String notes, List<String> tags, String link,
        List<String> events, List<UpdateDocumentPageRequest> pages) {

    public UpdateDocumentRequest {
        name = name == null ? "" : name;
        notes = notes == null ? "" : notes;
        link = link == null ? "" : link;
        tags = tags == null ? List.of() : List.copyOf(tags);
        events = events == null ? List.of() : List.copyOf(events);
        pages = pages == null ? List.of() : List.copyOf(pages);
    }
}
