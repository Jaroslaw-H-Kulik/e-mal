package com.emal.genealogy.service;

import com.emal.genealogy.model.FlexibleDate;

/**
 * The `{year, month, day, circa}` shape used by person birth/death dates and
 * event dates on the wire. Mirrors RequestValues.toFlexibleDate: year/month/day
 * pass through as given (null if omitted), circa defaults to false if
 * omitted or explicitly null - `circa` must stay boxed {@link Boolean}, not
 * primitive: Jackson 3's record binding passes a literal `null` through for
 * a missing/null JSON property rather than a primitive default, and fails
 * the whole request with a 400 if the target field is primitive (verified
 * against a live server - see the plan's Group D notes).
 */
public record DateRequest(Integer year, Integer month, Integer day, Boolean circa) {

    public DateRequest {
        circa = circa != null && circa;
    }

    public FlexibleDate toFlexibleDate() {
        return new FlexibleDate(year, month, day, circa);
    }

    /** Null-safe conversion for an optional/absent `date` field on an outer request. */
    public static FlexibleDate toFlexibleDateOrNull(DateRequest date) {
        return date == null ? null : date.toFlexibleDate();
    }
}
