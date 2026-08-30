package com.emal.genealogy.service;

import com.emal.genealogy.model.FlexibleDate;
import java.util.List;
import java.util.Map;
import java.util.NoSuchElementException;

/**
 * Shared helpers for reading raw request maps (Map&lt;String, Object&gt;,
 * as deserialized from a JSON request body) the same
 * presence/truthiness-aware way Python's `.get()` chains do. Used by every
 * service that accepts a raw request body instead of a strict DTO - see
 * PersonService's javadoc for why a DTO doesn't fit this codebase's
 * request shapes.
 */
public final class RequestValues {

    private RequestValues() {
    }

    /** Mirrors {@code data.get(primaryKey, data.get(fallbackKey, defaultValue))}: key PRESENCE, not truthiness. */
    public static String stringOrDefault(Map<String, Object> data, String primaryKey, String fallbackKey, String defaultValue) {
        if (data.containsKey(primaryKey)) {
            return asStringOrNull(data.get(primaryKey));
        }
        if (fallbackKey != null && data.containsKey(fallbackKey)) {
            return asStringOrNull(data.get(fallbackKey));
        }
        return defaultValue;
    }

    public static String asStringOrNull(Object value) {
        return value == null ? null : value.toString();
    }

    /**
     * Mirrors {@code data[key]} (direct dict indexing, not {@code .get()}):
     * throws if the key is absent, with a message shaped like Python's
     * {@code str(KeyError(key))} ({@code "'key'"}, quotes included) - so a
     * caller that surfaces {@code e.getMessage()} as its error field (see
     * RelationshipService.addRelationship, which ports add_relationship's
     * required-but-unvalidated {@code rel_data['role']} etc.) produces the
     * same error text Python's uncaught KeyError would.
     */
    public static String requireString(Map<String, Object> data, String key) {
        if (!data.containsKey(key)) {
            throw new NoSuchElementException("'" + key + "'");
        }
        return asStringOrNull(data.get(key));
    }

    /** Mirrors {@code if data.get(key):} - truthy check (null/empty string both false), not presence. */
    public static String truthyString(Map<String, Object> data, String key) {
        return truthy(data.get(key));
    }

    /** Mirrors {@code value or None} on a plain value already in hand (not looked up from a map). */
    public static String truthy(Object value) {
        if (value == null) {
            return null;
        }
        String s = value.toString();
        return s.isEmpty() ? null : s;
    }

    public static boolean isTruthy(Object value) {
        if (value == null) {
            return false;
        }
        if (value instanceof String s) {
            return !s.isEmpty();
        }
        if (value instanceof Map<?, ?> m) {
            return !m.isEmpty();
        }
        if (value instanceof List<?> l) {
            return !l.isEmpty();
        }
        if (value instanceof Number n) {
            return n.doubleValue() != 0;
        }
        if (value instanceof Boolean b) {
            return b;
        }
        return true;
    }

    public static Integer toInteger(Object value) {
        if (value == null) {
            return null;
        }
        if (value instanceof Number number) {
            return number.intValue();
        }
        return Integer.parseInt(value.toString());
    }

    /**
     * Mirrors the Python reference's new normalize_date() helper
     * (app/genealogy_repository.py): year/month/day default to null,
     * circa defaults to false - never omitted. Returns null unchanged.
     */
    public static FlexibleDate toFlexibleDate(Map<String, Object> dateMap) {
        if (dateMap == null) {
            return null;
        }
        boolean circa = Boolean.TRUE.equals(dateMap.get("circa"));
        return new FlexibleDate(
                toInteger(dateMap.get("year")), toInteger(dateMap.get("month")), toInteger(dateMap.get("day")), circa);
    }

    @SuppressWarnings("unchecked")
    public static Map<String, Object> asMap(Object value) {
        return value instanceof Map<?, ?> ? (Map<String, Object>) value : null;
    }

    @SuppressWarnings("unchecked")
    public static List<Map<String, Object>> asListOfMaps(Object value) {
        if (!(value instanceof List<?> list)) {
            return List.of();
        }
        return (List<Map<String, Object>>) (List<?>) list;
    }

    /** Mirrors {@code data.get(key, [])}: absent key -> empty list; non-list value -> empty list (Python never validates this either). */
    public static List<String> stringList(Object value) {
        if (value instanceof List<?> list) {
            return list.stream().map(String::valueOf).toList();
        }
        return List.of();
    }
}
