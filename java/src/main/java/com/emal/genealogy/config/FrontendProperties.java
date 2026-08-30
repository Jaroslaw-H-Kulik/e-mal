package com.emal.genealogy.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Path to the served frontend directory (web/) - kept as its own readable
 * property (rather than parsing it back out of
 * spring.web.resources.static-locations) so SpaRoutingController can find
 * index.html on disk directly. Named "Frontend" rather than "Web" to avoid
 * colliding with Spring Boot's own
 * org.springframework.boot.autoconfigure.web.WebProperties.
 */
@ConfigurationProperties(prefix = "web")
public record FrontendProperties(String root) {
}
