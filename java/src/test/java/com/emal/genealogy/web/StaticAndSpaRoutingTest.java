package com.emal.genealogy.web;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.resttestclient.TestRestTemplate;
import org.springframework.boot.resttestclient.autoconfigure.AutoConfigureTestRestTemplate;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.SpringBootTest.WebEnvironment;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

/**
 * Web-layer integration tests for static/SPA routing - the one layer this
 * project's service-level golden tests (see GoldenFileTestSupport) can't
 * exercise, since it's about HTTP routing and static-file serving, not
 * business logic. Boots the real Spring context on a random port, against
 * a sandboxed copy of the data file (never the real
 * data/genealogy_new_model.json - same sandboxing discipline
 * GoldenFileTestSupport uses for service tests), and drives it with real
 * HTTP requests via TestRestTemplate - the automated equivalent of the
 * curl-based smoke tests StaticResourceConfig/SpaRoutingController were
 * verified with manually.
 */
@SpringBootTest(webEnvironment = WebEnvironment.RANDOM_PORT)
@AutoConfigureTestRestTemplate
class StaticAndSpaRoutingTest {

    @TempDir
    static Path tempDir;

    @Autowired
    private TestRestTemplate restTemplate;

    @DynamicPropertySource
    static void sandboxDataFile(DynamicPropertyRegistry registry) throws IOException {
        Path sandboxDataFile = tempDir.resolve("genealogy_new_model.json");
        Files.writeString(
                sandboxDataFile,
                "{\"persons\":{},\"places\":{},\"events\":{},\"event_participations\":{},\"metadata\":{}}",
                StandardCharsets.UTF_8);
        registry.add("data.file", sandboxDataFile::toString);
    }

    @Test
    void dataDirectoryIsServedAsStaticFiles() {
        ResponseEntity<String> response = restTemplate.getForEntity("/data/genealogy_new_model.json", String.class);

        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertTrue(response.getBody().contains("\"persons\""));
    }

    @Test
    void dataDirectoryDoesNotServeFilesThatDontExist() {
        ResponseEntity<String> response = restTemplate.getForEntity("/data/does-not-exist.json", String.class);

        assertEquals(HttpStatus.NOT_FOUND, response.getStatusCode());
    }

    @Test
    void webAssetsReferencedByIndexHtmlAreServedUnderWebPrefix() {
        // Regression test: index.html itself links every asset with an
        // absolute /web/... prefix (<link href="/web/style.css">,
        // <script src="/web/app.js">, etc.) - a real browser hitting the
        // Java backend for the first time got a page with no CSS/JS at
        // all, because the bare "/**" -> web/ mapping alone resolves
        // "/web/style.css" as the doubled path "web/web/style.css".
        ResponseEntity<String> css = restTemplate.getForEntity("/web/style.css", String.class);
        assertEquals(HttpStatus.OK, css.getStatusCode());

        ResponseEntity<String> appJs = restTemplate.getForEntity("/web/app.js", String.class);
        assertEquals(HttpStatus.OK, appJs.getStatusCode());
    }

    @Test
    void spaRoutingServesIndexHtmlForEventsAndPersonUrls() {
        assertServesIndexHtml("/events");
        assertServesIndexHtml("/person/P0001");
        assertServesIndexHtml("/person/P0001/nested");
    }

    @Test
    void spaRoutingExcludesBarePersonAndDocumentUrls() {
        assertEquals(HttpStatus.NOT_FOUND, restTemplate.getForEntity("/person", String.class).getStatusCode());
        assertEquals(HttpStatus.NOT_FOUND, restTemplate.getForEntity("/document/foo", String.class).getStatusCode());
    }

    private void assertServesIndexHtml(String path) {
        ResponseEntity<String> response = restTemplate.getForEntity(path, String.class);

        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertTrue(response.getHeaders().getContentType() != null
                && response.getHeaders().getContentType().toString().contains("text/html"));
        assertTrue(response.getBody().contains("<!DOCTYPE html"));
    }
}
