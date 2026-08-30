package com.emal.genealogy.golden;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.fail;

import com.emal.genealogy.config.DataProperties;
import com.emal.genealogy.model.Event;
import com.emal.genealogy.model.EventParticipation;
import com.emal.genealogy.model.Person;
import com.emal.genealogy.model.Place;
import com.emal.genealogy.repository.GenealogyRepository;
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
 * Java equivalent of tests/golden_utils.py's Layer 1 golden-master
 * mechanics: sandbox a copy of the real data file (mirrors
 * tests/conftest.py's live_server fixture), snapshot repository state
 * before/after a service call, diff it the same way
 * (golden_utils.dict_diff/state_diff), replace any id the call *created*
 * with a stable placeholder (golden_utils._new_id_placeholders), and
 * compare the serialized {response, diff} against the fixture text in
 * tests/golden/ - the SAME fixtures the Python tests use as the oracle
 * (referenced directly, not copied - see JAVA_MIGRATION.md's folder
 * structure note on this).
 */
public final class GoldenFileTestSupport {

    private static final Path REAL_DATA_FILE = Path.of("../data/genealogy_new_model.json");
    private static final Path GOLDEN_DIR = Path.of("../tests/golden");

    // Order matches golden_utils.ID_PLACEHOLDER_PREFIXES.
    private static final Map<String, String> ID_PREFIXES = new LinkedHashMap<>();

    static {
        ID_PREFIXES.put("persons", "P");
        ID_PREFIXES.put("places", "PL");
        ID_PREFIXES.put("events", "E");
        ID_PREFIXES.put("event_participations", "EP");
    }

    // sort_keys=True equivalent (MapperFeature/SerializationFeature) plus the
    // same CRLF pretty-printer style as GenealogyJsonMapper, since the
    // fixture files were written by Python's Path.write_text on Windows.
    private static final JsonMapper MAPPER = buildMapper();

    private GoldenFileTestSupport() {
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

    /**
     * sort_keys=True equivalent. MapperFeature.SORT_PROPERTIES_ALPHABETICALLY
     * does not reorder record-component-derived properties in Jackson 3, so
     * key order has to be forced by rebuilding the tree instead of relying
     * on a mapper feature.
     */
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

    /** Copies the real data file into tempDir (never touches the real file) and loads a repository from the copy. */
    public static GenealogyRepository freshRepository(Path tempDir) throws IOException {
        Path sandboxFile = tempDir.resolve("genealogy_new_model.json");
        Files.copy(REAL_DATA_FILE, sandboxFile, StandardCopyOption.REPLACE_EXISTING);
        GenealogyRepository repository = new GenealogyRepository(new DataProperties(sandboxFile.toString()));
        repository.load();
        return repository;
    }

    public record EntitySnapshot(
            Map<String, Person> persons,
            Map<String, Place> places,
            Map<String, Event> events,
            Map<String, EventParticipation> eventParticipations
    ) {
    }

    /** Shallow-copies the repository's live maps - safe since Person/Event/Place/EventParticipation are immutable records. */
    public static EntitySnapshot snapshot(GenealogyRepository repository) {
        return new EntitySnapshot(
                new LinkedHashMap<>(repository.persons()),
                new LinkedHashMap<>(repository.places()),
                new LinkedHashMap<>(repository.events()),
                new LinkedHashMap<>(repository.eventParticipations()));
    }

    /**
     * Asserts {response, diff(before, after)} - with any newly-created id
     * replaced by a stable placeholder - matches tests/golden/{name}.json.
     * Writes the fixture and fails loudly on first run, exactly like
     * golden_utils.assert_matches_golden.
     */
    public static void assertMatchesGolden(String name, Object response, EntitySnapshot before, EntitySnapshot after)
            throws IOException {
        assertMatchesGolden(name, response, before, after, List.of());
    }

    /**
     * Same as {@link #assertMatchesGolden(String, Object, EntitySnapshot, EntitySnapshot)},
     * but also normalizes ids created by earlier setup-call diffs (mirrors
     * golden_utils.assert_matches_golden's extra_new_id_diffs param - see
     * its docstring and test_update_event.py's combined test) - only the
     * main before/after diff is persisted to the fixture, extraDiffs are
     * used solely to make id-placeholder assignment deterministic.
     */
    public static void assertMatchesGolden(
            String name, Object response, EntitySnapshot before, EntitySnapshot after,
            List<Map<String, Object>> extraDiffs) throws IOException {
        Map<String, Object> diff = stateDiff(before, after);
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

    /** Exposed so a test needing an uncovered setup call first (see test_update_event.py's combined test) can pass its diff to extraDiffs. */
    public static Map<String, Object> stateDiff(EntitySnapshot before, EntitySnapshot after) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("persons", dictDiff(before.persons(), after.persons()));
        result.put("places", dictDiff(before.places(), after.places()));
        result.put("events", dictDiff(before.events(), after.events()));
        result.put("event_participations", dictDiff(before.eventParticipations(), after.eventParticipations()));
        return result;
    }

    private static <V> Map<String, Object> dictDiff(Map<String, V> before, Map<String, V> after) {
        Map<String, Object> added = new LinkedHashMap<>();
        Map<String, Object> removed = new LinkedHashMap<>();
        Map<String, Object> changed = new LinkedHashMap<>();

        for (Map.Entry<String, V> entry : after.entrySet()) {
            if (!before.containsKey(entry.getKey())) {
                added.put(entry.getKey(), entry.getValue());
            }
        }
        for (Map.Entry<String, V> entry : before.entrySet()) {
            if (!after.containsKey(entry.getKey())) {
                removed.put(entry.getKey(), entry.getValue());
            }
        }
        for (Map.Entry<String, V> entry : after.entrySet()) {
            V beforeValue = before.get(entry.getKey());
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
        Map<String, String> mapping = new LinkedHashMap<>();
        for (Map.Entry<String, String> entityPrefix : ID_PREFIXES.entrySet()) {
            Map<String, Object> seenIds = new LinkedHashMap<>();
            for (Map<String, Object> diff : diffs) {
                Map<String, Object> entityDiff = (Map<String, Object>) diff.get(entityPrefix.getKey());
                Map<String, Object> added = (Map<String, Object>) entityDiff.get("added");
                for (String realId : added.keySet()) {
                    seenIds.put(realId, null);
                }
            }
            List<String> ordered = seenIds.keySet().stream()
                    .sorted(Comparator.comparingInt(id -> Integer.parseInt(id.replaceAll("\\D", ""))))
                    .toList();
            int i = 1;
            for (String realId : ordered) {
                mapping.put(realId, entityPrefix.getValue() + "_NEW_" + i);
                i++;
            }
        }
        return mapping;
    }
}
