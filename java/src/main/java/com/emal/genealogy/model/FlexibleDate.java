package com.emal.genealogy.model;

/**
 * year/month/day/circa are always all present (with null year/month/day and
 * circa=false when unknown) - this shape was normalized by
 * normalize_data_schema.py's DATE_FIELDS pass specifically so this can be a
 * plain record with no custom (de)serializer.
 */
public record FlexibleDate(Integer year, Integer month, Integer day, boolean circa) {
}
