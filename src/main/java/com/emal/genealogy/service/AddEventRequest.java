package com.emal.genealogy.service;

import java.util.List;

/**
 * JSON body for POST /api/add-event, sent by event-editor.js's saveEvent
 * (and, in a minimal shape - no place/title/tags/links/notes/content, only
 * type/date/participants - by maybeCreateMarriageForParents). `notes`
 * defaults to "" (was RequestValues.stringOrDefault); `placeName`/`content`
 * collapse blank to null (was RequestValues.truthyString); `tags`/`links`/
 * `participants` default to an empty list.
 */
public record AddEventRequest(
        String type, DateRequest date, String placeName, String houseNumber, String title, String notes,
        List<String> tags, List<String> links, String content, List<EventParticipantRequest> participants) {

    public AddEventRequest {
        notes = notes == null ? "" : notes;
        placeName = placeName == null || placeName.isEmpty() ? null : placeName;
        content = content == null || content.isEmpty() ? null : content;
        tags = tags == null ? List.of() : List.copyOf(tags);
        links = links == null ? List.of() : List.copyOf(links);
        participants = participants == null ? List.of() : List.copyOf(participants);
    }
}
