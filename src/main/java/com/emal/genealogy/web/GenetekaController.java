package com.emal.genealogy.web;

import com.emal.genealogy.service.GenetekaImportResult;
import com.emal.genealogy.service.GenetekaService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * Thin HTTP layer over GenetekaService - ports server.py's do_GET
 * special-case for paths starting with /api/geneteka-import. Query
 * parameter names are snake_case to match web/app.js's fetch calls exactly
 * (unlike request/response bodies elsewhere, Spring's SNAKE_CASE Jackson
 * naming strategy doesn't apply to @RequestParam, so the names are spelled
 * out explicitly here).
 */
@RestController
public class GenetekaController {

    private final GenetekaService genetekaService;

    public GenetekaController(GenetekaService genetekaService) {
        this.genetekaService = genetekaService;
    }

    @GetMapping("/api/geneteka-import")
    public GenetekaImportResult genetekaImport(
            @RequestParam(name = "first_name", defaultValue = "") String firstName,
            @RequestParam(name = "last_name", defaultValue = "") String lastName,
            @RequestParam(name = "type", defaultValue = "birth") String recordType) {
        return genetekaService.importRecords(firstName, lastName, recordType);
    }
}
