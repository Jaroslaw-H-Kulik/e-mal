package com.emal.genealogy.service;

import java.util.List;
import java.util.Map;

/**
 * Mirrors geneteka_import's two return shapes (server.py) - a plain
 * success/error result, never an exception (see AddPersonResult's javadoc
 * for the same rationale). Field sets genuinely differ per branch, not
 * just their values: the success dict has no "error" key and the failure
 * dict has no "total" key, so this is modeled the same way rather than as
 * one record with always-present fields.
 */
public sealed interface GenetekaImportResult {

    record Success(boolean success, List<Map<String, Object>> records, Object total) implements GenetekaImportResult {
        public Success(List<Map<String, Object>> records, Object total) {
            this(true, records, total);
        }
    }

    record Failure(boolean success, String error, List<Map<String, Object>> records) implements GenetekaImportResult {
        public Failure(String error) {
            this(false, error, List.of());
        }
    }
}
