package com.emal.genealogy.golden;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.fail;

import com.emal.genealogy.config.DocumentDataProperties;
import com.emal.genealogy.model.Document;
import com.emal.genealogy.repository.DocumentRepository;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;
import tools.jackson.core.util.DefaultIndenter;
import tools.jackson.core.util.DefaultPrettyPrinter;
import tools.jackson.core.util.Separators;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.PropertyNamingStrategies;
import tools.jackson.databind.SerializationFeature;
import tools.jackson.databind.json.JsonMapper;
import tools.jackson.databind.node.ArrayNode;
import tools.jackson.databind.node.JsonNodeFactory;
import tools.jackson.databind.node.ObjectNode;

/**
 * Documents-specific golden-master helper, parallel to (but distinct from)
 * GoldenFileTestSupport - see JAVA_MIGRATION.md's "Document management
 * port" section for why: data/documents.json is a single flat
 * {@code {doc_id: document}} map (one entity type, D##-prefixed ids), not
 * GenealogyRepository's four collections, so GoldenFileTestSupport's
 * EntitySnapshot/stateDiff/id-prefix machinery doesn't fit directly. Mirrors
 * tests/documents_golden_utils.py's split from golden_utils.py on the
 * Python side.
 */
public final class DocumentGoldenFileTestSupport {

    private static final Path REAL_DATA_FILE = Path.of("data/documents.json");
    private static final Path GOLDEN_DIR = Path.of("src/test/resources/golden");
    private static final String ID_PREFIX = "D";

    private static final JsonMapper MAPPER = buildMapper();

    private DocumentGoldenFileTestSupport() {
    }

    private static JsonMapper buildMapper() {
        DefaultIndenter indenter = new DefaultIndenter("  ", "\r\n");
        Separators separators = Separators.createDefaultInstance()
                .withObjectNameValueSpacing(Separators.Spacing.AFTER)
                .withObjectEmptySeparator("")
                .withArrayEmptySeparator("");
        DefaultPrettyPrinter prettyPrinter = new DefaultPrettyPrinter(separators)
                .withObjectIndenter(indenter)
                .withArrayIndenter(indenter);

        return JsonMapper.builder()
                .propertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE)
                .defaultPrettyPrinter(prettyPrinter)
                .enable(SerializationFeature.INDENT_OUTPUT)
                .build();
    }

    private static JsonNode sortRecursively(JsonNode node) {
        if (node.isObject()) {
            ObjectNode sorted = JsonNodeFactory.instance.objectNode();
            node.properties().stream()
                    .sorted(Map.Entry.comparingByKey())
                    .forEach(entry -> sorted.set(entry.getKey(), sortRecursively(entry.getValue())));
            return sorted;
        }
        if (node.isArray()) {
            ArrayNode sorted = JsonNodeFactory.instance.arrayNode();
            for (JsonNode element : (ArrayNode) node) {
                sorted.add(sortRecursively(element));
            }
            return sorted;
        }
        return node;
    }

    /** Copies the real documents.json into tempDir (never touches the real file) and loads a repository from the copy. */
    public static DocumentRepository freshRepository(Path tempDir) throws IOException {
        Path sandboxFile = tempDir.resolve("documents.json");
        Files.copy(REAL_DATA_FILE, sandboxFile, StandardCopyOption.REPLACE_EXISTING);
        DocumentRepository repository = new DocumentRepository(new DocumentDataProperties(sandboxFile.toString()));
        repository.load();
        return repository;
    }

    /** Shallow-copies the repository's live map - safe since Document is an immutable record. */
    public static Map<String, Document> snapshot(DocumentRepository repository) {
        return new LinkedHashMap<>(repository.documents());
    }

    public static void assertMatchesGolden(
            String name, Object response, Map<String, Document> before, Map<String, Document> after)
            throws IOException {
        assertMatchesGolden(name, response, before, after, List.of());
    }

    /**
     * Same as the 4-arg overload, but also normalizes ids created by
     * earlier setup-call diffs - mirrors GoldenFileTestSupport's
     * extraDiffs overload (see its javadoc and test_update_event.py's
     * combined test) - only the main before/after diff is persisted to
     * the fixture, extraDiffs are used solely to make id-placeholder
     * assignment deterministic.
     */
    public static void assertMatchesGolden(
            String name, Object response, Map<String, Document> before, Map<String, Document> after,
            List<Map<String, Object>> extraDiffs) throws IOException {
        Map<String, Object> diff = dictDiff(before, after);
        Map<String, Object> actual = new LinkedHashMap<>();
        actual.put("response", response);
        actual.put("diff", diff);

        List<Map<String, Object>> allDiffs = new ArrayList<>(extraDiffs);
        allDiffs.add(diff);
        Map<String, String> idPlaceholders = newIdPlaceholders(allDiffs);

        JsonNode sortedTree = sortRecursively(MAPPER.valueToTree(actual));
        String serialized = MAPPER.writeValueAsString(sortedTree);
        for (Map.Entry<String, String> entry : idPlaceholders.entrySet()) {
            serialized = Pattern.compile("\\b" + Pattern.quote(entry.getKey()) + "\\b")
                    .matcher(serialized)
                    .replaceAll(entry.getValue());
        }

        Path path = GOLDEN_DIR.resolve(name + ".json");
        if (!Files.exists(path)) {
            Files.writeString(path, serialized, StandardCharsets.UTF_8);
            fail("No golden fixture yet - wrote a new one from this run's output: " + path
                    + "\nReview it, then re-run the test so it's checked against a fixture instead of writing one.");
        }

        String expected = Files.readString(path, StandardCharsets.UTF_8);
        assertEquals(expected, serialized, "Result diverged from golden fixture " + path
                + "\nIf this divergence is an intended behavior change, delete the fixture and re-run to regenerate it.");
    }

    /** Exposed so a test needing an uncovered setup call first (e.g. an add-document call to get a real doc id) can pass its diff to extraDiffs. */
    public static Map<String, Object> dictDiff(Map<String, Document> before, Map<String, Document> after) {
        Map<String, Object> added = new LinkedHashMap<>();
        Map<String, Object> removed = new LinkedHashMap<>();
        Map<String, Object> changed = new LinkedHashMap<>();

        for (Map.Entry<String, Document> entry : after.entrySet()) {
            if (!before.containsKey(entry.getKey())) {
                added.put(entry.getKey(), entry.getValue());
            }
        }
        for (Map.Entry<String, Document> entry : before.entrySet()) {
            if (!after.containsKey(entry.getKey())) {
                removed.put(entry.getKey(), entry.getValue());
            }
        }
        for (Map.Entry<String, Document> entry : after.entrySet()) {
            Document beforeValue = before.get(entry.getKey());
            if (beforeValue != null && !beforeValue.equals(entry.getValue())) {
                Map<String, Object> pair = new LinkedHashMap<>();
                pair.put("before", beforeValue);
                pair.put("after", entry.getValue());
                changed.put(entry.getKey(), pair);
            }
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("added", added);
        result.put("removed", removed);
        result.put("changed", changed);
        return result;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, String> newIdPlaceholders(List<Map<String, Object>> diffs) {
        Map<String, Object> seenIds = new LinkedHashMap<>();
        for (Map<String, Object> diff : diffs) {
            Map<String, Object> added = (Map<String, Object>) diff.get("added");
            for (String realId : added.keySet()) {
                seenIds.put(realId, null);
            }
        }
        List<String> ordered = seenIds.keySet().stream()
                .sorted(Comparator.comparingInt(id -> Integer.parseInt(id.replaceAll("\\D", ""))))
                .toList();

        Map<String, String> mapping = new LinkedHashMap<>();
        int i = 1;
        for (String realId : ordered) {
            mapping.put(realId, ID_PREFIX + "_NEW_" + i);
            i++;
        }
        return mapping;
    }
}
