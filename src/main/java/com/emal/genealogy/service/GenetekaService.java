package com.emal.genealogy.service;

import java.io.IOException;
import java.net.CookieManager;
import java.net.CookiePolicy;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.springframework.stereotype.Component;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

/**
 * Ports geneteka_import (server.py's GenealogyServerHandler): proxies a
 * name search to geneteka.genealodzy.pl and parses birth/marriage/death
 * result rows out of its HTML-embedded JSON API. Two-step session flow
 * (an HTML page visit to pick up cookies, then the JSON API call using
 * them) is required - the API returns empty data without a session
 * cookie, matching Python's http.cookiejar-backed urllib opener.
 */
@Component
public class GenetekaService {

    private static final Pattern IMG_TITLE = Pattern.compile("<img[^>]+title=\"([^\"]*)\"");
    private static final Pattern HREF_LINK = Pattern.compile("href=\"(https?://[^\"]+)\"");
    private static final Pattern HTML_TAG = Pattern.compile("<[^>]+>");
    private static final String USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            + "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";
    private static final String ACCEPT_LANGUAGE = "pl,en;q=0.9";
    private static final Duration TIMEOUT = Duration.ofSeconds(15);
    private static final Map<String, String[]> TYPE_CONFIG = Map.of(
            "birth", new String[] {"B", "3382"},
            "marriage", new String[] {"S", "3560"},
            "death", new String[] {"D", "3384"});

    private final JsonMapper jsonMapper = JsonMapper.builder().build();

    public GenetekaImportResult importRecords(String firstName, String lastName, String recordType) {
        String[] config = TYPE_CONFIG.getOrDefault(recordType, TYPE_CONFIG.get("birth"));
        String bdm = config[0];
        String rid = config[1];

        try {
            String encodedLast = quote(lastName);
            String encodedFirst = quote(firstName);

            CookieManager cookieManager = new CookieManager(null, CookiePolicy.ACCEPT_ALL);
            HttpClient client = HttpClient.newBuilder()
                    .cookieHandler(cookieManager)
                    .connectTimeout(TIMEOUT)
                    .build();

            String indexUrl = "https://geneteka.genealodzy.pl/index.php"
                    + "?op=gt&lang=pol&bdm=" + bdm + "&w=13sk&rid=" + rid
                    + "&search_lastname=" + encodedLast + "&search_name=" + encodedFirst
                    + "&search_lastname2=&search_name2=&from_date=&to_date=";
            HttpRequest indexRequest = HttpRequest.newBuilder(URI.create(indexUrl))
                    .header("User-Agent", USER_AGENT)
                    .header("Accept", "text/html")
                    .header("Accept-Language", ACCEPT_LANGUAGE)
                    .timeout(TIMEOUT)
                    .GET()
                    .build();
            // Response body is discarded - this call exists only to make the
            // session cookies land in cookieManager before the API call.
            client.send(indexRequest, HttpResponse.BodyHandlers.discarding());

            String apiUrl = "https://geneteka.genealodzy.pl/api/getAct.php"
                    + "?op=gt&lang=pol&bdm=" + bdm + "&w=13sk&rid=" + rid
                    + "&search_lastname=" + encodedLast + "&search_name=" + encodedFirst
                    + "&search_lastname2=&search_name2=&from_date=&to_date="
                    + "&draw=1&start=0&length=100";
            HttpRequest apiRequest = HttpRequest.newBuilder(URI.create(apiUrl))
                    .header("User-Agent", USER_AGENT)
                    .header("Referer", indexUrl)
                    .header("Accept", "application/json")
                    .header("Accept-Language", ACCEPT_LANGUAGE)
                    .header("X-Requested-With", "XMLHttpRequest")
                    .timeout(TIMEOUT)
                    .GET()
                    .build();
            HttpResponse<String> apiResponse =
                    client.send(apiRequest, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));

            JsonNode data = jsonMapper.readTree(apiResponse.body());
            List<Map<String, Object>> records = new ArrayList<>();
            for (JsonNode row : data.path("data")) {
                Map<String, Object> record = parseRow(recordType, row);
                if (record != null) {
                    records.add(record);
                }
            }

            Object total = data.has("recordsTotal") ? data.get("recordsTotal").asInt() : records.size();
            return new GenetekaImportResult.Success(records, total);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return new GenetekaImportResult.Failure(String.valueOf(e.getMessage()));
        } catch (IOException | RuntimeException e) {
            return new GenetekaImportResult.Failure(e.getMessage() != null ? e.getMessage() : e.toString());
        }
    }

    private static Map<String, Object> parseRow(String recordType, JsonNode row) {
        if (!row.isArray()) {
            return null;
        }
        int size = row.size();
        return switch (recordType) {
            case "marriage" -> parseMarriageRow(row, size);
            case "death" -> parseDeathRow(row, size);
            default -> parseBirthRow(row, size);
        };
    }

    private static Map<String, Object> parseMarriageRow(JsonNode row, int size) {
        // 10 columns: rok, akt, groom_name, groom_surname, groom_parents,
        //             bride_name, bride_surname, bride_parents, place, uwagi
        if (size < 9) {
            return null;
        }
        String uwagiHtml = size > 9 ? text(row, 9) : "";
        String rodzicePana = cell(row, 4);
        String rodzicePani = cell(row, 7);

        Map<String, Object> record = new LinkedHashMap<>();
        record.put("rok", cell(row, 0));
        record.put("akt", cell(row, 1));
        record.put("imie_pana", cell(row, 2));
        record.put("nazwisko_pana", cell(row, 3));
        record.put("rodzice_pana", rodzicePana);
        record.put("imie_pani", cell(row, 5));
        record.put("nazwisko_pani", cell(row, 6));
        record.put("rodzice_pani", rodzicePani);
        record.put("miejscowosc", cell(row, 8));
        record.put("uwagi", extractUwagi(uwagiHtml));
        record.put("links", extractLinks(uwagiHtml));
        record.put("rodzice_pana_parsed", parseRodzice(rodzicePana));
        record.put("rodzice_pani_parsed", parseRodzice(rodzicePani));
        return record;
    }

    private static Map<String, Object> parseDeathRow(JsonNode row, int size) {
        // 9 columns: rok, akt, name, surname, father, mother, mother_maiden, place, uwagi
        if (size < 8) {
            return null;
        }
        String uwagiHtml = size > 8 ? text(row, 8) : "";

        Map<String, Object> record = new LinkedHashMap<>();
        record.put("rok", cell(row, 0));
        record.put("akt", cell(row, 1));
        record.put("imie", cell(row, 2));
        record.put("nazwisko", cell(row, 3));
        record.put("imie_ojca", cell(row, 4));
        record.put("imie_matki", cell(row, 5));
        record.put("nazwisko_matki", cell(row, 6));
        record.put("miejscowosc", cell(row, 7));
        record.put("uwagi", extractUwagi(uwagiHtml));
        record.put("links", extractLinks(uwagiHtml));
        return record;
    }

    private static Map<String, Object> parseBirthRow(JsonNode row, int size) {
        // 10 columns: rok, akt, child_name, surname, father, mother, mother_maiden, parish, place, uwagi
        // Some older/incomplete records have fewer columns - cell() defaults to "" past the row's end.
        if (size < 2) {
            return null;
        }
        String uwagiHtml = size > 9 ? text(row, 9) : "";

        Map<String, Object> record = new LinkedHashMap<>();
        record.put("rok", cell(row, 0));
        record.put("akt", cell(row, 1));
        record.put("imie_dziecka", cell(row, 2));
        record.put("nazwisko", cell(row, 3));
        record.put("imie_ojca", cell(row, 4));
        record.put("imie_matki", cell(row, 5));
        record.put("nazwisko_matki", cell(row, 6));
        record.put("parafia", cell(row, 7));
        record.put("miejscowosc", cell(row, 8));
        record.put("uwagi", extractUwagi(uwagiHtml));
        record.put("links", extractLinks(uwagiHtml));
        return record;
    }

    private static Map<String, Object> parseRodzice(String rodzice) {
        Map<String, Object> parsed = new LinkedHashMap<>();
        if (rodzice == null || rodzice.strip().isEmpty()) {
            parsed.put("father_name", "");
            parsed.put("mother_name", "");
            parsed.put("mother_maiden", "");
            return parsed;
        }
        String[] parts = rodzice.split(",", 2);
        String fatherName = parts[0].strip();
        String motherPart = parts.length > 1 ? parts[1].strip() : "";
        String[] motherParts = motherPart.isEmpty() ? new String[0] : motherPart.split("\\s+");
        parsed.put("father_name", fatherName);
        parsed.put("mother_name", motherParts.length > 0 ? motherParts[0] : "");
        parsed.put("mother_maiden", motherParts.length > 1 ? motherParts[1] : "");
        return parsed;
    }

    private static String extractUwagi(String html) {
        List<String> parts = new ArrayList<>();
        Matcher matcher = IMG_TITLE.matcher(html);
        while (matcher.find()) {
            String title = matcher.group(1).strip();
            if (!title.isEmpty()) {
                parts.add(title);
            }
        }
        return String.join(" | ", parts);
    }

    private static List<String> extractLinks(String html) {
        List<String> links = new ArrayList<>();
        Matcher matcher = HREF_LINK.matcher(html);
        while (matcher.find()) {
            links.add(matcher.group(1));
        }
        return links;
    }

    private static String stripHtml(String text) {
        return HTML_TAG.matcher(text).replaceAll("").strip();
    }

    /** Raw (unstripped) column text, "" past the row's end - mirrors Python's `row[i] if len(row) > i else ''`. */
    private static String text(JsonNode row, int index) {
        return index < row.size() ? row.get(index).asText("") : "";
    }

    /** Tag-stripped, trimmed column text, "" past the row's end - mirrors Python's `strip_html(row[i]).strip()`. */
    private static String cell(JsonNode row, int index) {
        return stripHtml(text(row, index));
    }

    /** Mirrors urllib.parse.quote()'s percent-encoding (spaces as %20, not URLEncoder's form-style '+'). */
    private static String quote(String value) {
        return URLEncoder.encode(value, StandardCharsets.UTF_8).replace("+", "%20");
    }
}
