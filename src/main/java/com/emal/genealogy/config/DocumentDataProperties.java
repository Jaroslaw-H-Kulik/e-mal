package com.emal.genealogy.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Path to data/documents.json - a separate file/store from
 * genealogy_new_model.json (see DataProperties), so it gets its own
 * property rather than a second field on DataProperties (which would break
 * every existing single-arg {@code new DataProperties(file)} call site).
 * DocumentRepository derives the page-image directory
 * (data/documents/) from this same path's parent, mirroring server.py's
 * {@code _documents_dir()} deriving from {@code _documents_path()}.
 */
@ConfigurationProperties(prefix = "documents")
public record DocumentDataProperties(String file) {
}
