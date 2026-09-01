package com.emal.genealogy.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "data")
public record DataProperties(String file) {
}
