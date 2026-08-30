package com.emal.genealogy.config;

import org.springframework.boot.jackson.autoconfigure.JsonMapperBuilderCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import tools.jackson.databind.PropertyNamingStrategies;

/**
 * Spring Boot 4's Jackson 3 auto-configuration (JacksonAutoConfiguration,
 * spring-boot-jackson) applies any JsonMapperBuilderCustomizer bean to the
 * JsonMapper it builds for HTTP message conversion. Without this, Spring
 * MVC would serialize @RestController responses with camelCase field
 * names (e.g. "createdEvents"), breaking the REST contract server.py's
 * frontend (web/) expects ("created_events") - the same naming this
 * project already uses for the on-disk data file
 * (GenealogyJsonMapper). This is HTTP-layer only; file I/O keeps its own
 * separately-configured mapper.
 */
@Configuration
public class JacksonConfig {

    @Bean
    JsonMapperBuilderCustomizer snakeCaseNamingCustomizer() {
        return builder -> builder.propertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE);
    }
}
