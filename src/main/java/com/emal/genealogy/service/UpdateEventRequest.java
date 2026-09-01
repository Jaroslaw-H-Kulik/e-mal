package com.emal.genealogy.service;

import java.util.List;

/**
 * JSON body for POST /api/update-event - same shape as AddEventRequest plus
 * `eventId`, sent by event-editor.js's saveEvent when editing (the payload
 * is `{ event_id, ...eventData }`). See AddEventRequest's javadoc for the
 * per-field normalization rationale.
 */
public record UpdateEventRequest(
        String eventId, String type, DateRequest date, String placeName, String houseNumber, String title,
        String notes, List<String> tags, List<String> links, String content,
        List<EventParticipantRequest> participants) {

    public UpdateEventRequest {
        notes = notes == null ? "" : notes;
        placeName = placeName == null || placeName.isEmpty() ? null : placeName;
        content = content == null || content.isEmpty() ? null : content;
        tags = tags == null ? List.of() : List.copyOf(tags);
        links = links == null ? List.of() : List.copyOf(links);
        participants = participants == null ? List.of() : List.copyOf(participants);
    }
}
