package com.emal.genealogy.web;

import com.emal.genealogy.service.AddEventRequest;
import com.emal.genealogy.service.AddEventResult;
import com.emal.genealogy.service.DeleteEventRequest;
import com.emal.genealogy.service.DeleteEventResult;
import com.emal.genealogy.service.EventService;
import com.emal.genealogy.service.UpdateEventRequest;
import com.emal.genealogy.service.UpdateEventResult;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/** Thin HTTP layer over EventService - see PersonController's javadoc for the same shape/status-code rationale. */
@RestController
public class EventController {

    private final EventService eventService;

    public EventController(EventService eventService) {
        this.eventService = eventService;
    }

    @PostMapping("/api/add-event")
    public AddEventResult addEvent(@RequestBody AddEventRequest eventData) {
        return eventService.addEvent(eventData);
    }

    @PostMapping("/api/update-event")
    public UpdateEventResult updateEvent(@RequestBody UpdateEventRequest eventData) {
        return eventService.updateEvent(eventData);
    }

    @PostMapping("/api/delete-event")
    public DeleteEventResult deleteEvent(@RequestBody DeleteEventRequest requestData) {
        return eventService.deleteEvent(requestData);
    }
}
