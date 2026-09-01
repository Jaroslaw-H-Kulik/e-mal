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
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

/**
 * Live HTTP coverage for /api/save-data - the automated equivalent of the
 * manual curl smoke tests every prior porting step used (see
 * JAVA_MIGRATION.md's Status log). There's no Python golden fixture to
 * port a service-level test against here (see DataServiceTest's javadoc),
 * so this is the primary regression coverage for the endpoint's HTTP
 * contract: request binding, response shape, and that the sandboxed data
 * file on disk is actually overwritten.
 */
@SpringBootTest(webEnvironment = WebEnvironment.RANDOM_PORT)
@AutoConfigureTestRestTemplate
class DataControllerTest {

    @TempDir
    static Path tempDir;

    @Autowired
    private TestRestTemplate restTemplate;

    private static Path sandboxDataFile;

    @DynamicPropertySource
    static void sandboxDataFile(DynamicPropertyRegistry registry) throws IOException {
        sandboxDataFile = tempDir.resolve("genealogy_new_model.json");
        Files.writeString(
                sandboxDataFile,
                "{\"persons\":{},\"places\":{},\"events\":{},\"event_participations\":{},\"metadata\":{}}",
                StandardCharsets.UTF_8);
        registry.add("data.file", sandboxDataFile::toString);
    }

    @Test
    void saveDataOverwritesTheDataFileAndReturnsSuccessStatus() throws IOException {
        String requestBody = "{"
                + "\"persons\":{\"P0001\":{\"id\":\"P0001\",\"first_name\":\"Jan\",\"last_name\":\"Kowalski\","
                + "\"gender\":\"M\",\"maiden_name\":null,\"occupation\":null,\"tags\":[],\"notes\":null}},"
                + "\"places\":{},\"events\":{},\"event_participations\":{},"
                + "\"metadata\":{\"total_persons\":1}}";
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        ResponseEntity<String> response = restTemplate.postForEntity(
                "/api/save-data", new HttpEntity<>(requestBody, headers), String.class);

        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertTrue(response.getBody().contains("\"status\":\"success\""));
        assertTrue(response.getBody().contains("\"message\":\"Data saved successfully\""));

        String savedFile = Files.readString(sandboxDataFile, StandardCharsets.UTF_8);
        assertTrue(savedFile.contains("\"Jan\""));
        assertTrue(savedFile.contains("\"Kowalski\""));
    }

    @Test
    void saveDataReplacesRatherThanMergesExistingCollections() throws IOException {
        // Seed the sandbox with an existing person via a prior save, then
        // overwrite with a document that omits it - the whole-document
        // overwrite must drop it, unlike add/update-person's partial merges.
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        String seedBody = "{"
                + "\"persons\":{\"P0001\":{\"id\":\"P0001\",\"first_name\":\"Jan\",\"last_name\":\"Kowalski\","
                + "\"gender\":\"M\",\"maiden_name\":null,\"occupation\":null,\"tags\":[],\"notes\":null}},"
                + "\"places\":{},\"events\":{},\"event_participations\":{},\"metadata\":{}}";
        restTemplate.postForEntity("/api/save-data", new HttpEntity<>(seedBody, headers), String.class);

        String replacementBody = "{\"persons\":{},\"places\":{},\"events\":{},"
                + "\"event_participations\":{},\"metadata\":{}}";
        ResponseEntity<String> response = restTemplate.postForEntity(
                "/api/save-data", new HttpEntity<>(replacementBody, headers), String.class);

        assertEquals(HttpStatus.OK, response.getStatusCode());
        String savedFile = Files.readString(sandboxDataFile, StandardCharsets.UTF_8);
        assertTrue(savedFile.contains("\"persons\": {}"));
    }
}
