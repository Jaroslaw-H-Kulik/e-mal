package com.emal.genealogy.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.emal.genealogy.config.DataProperties;
import com.emal.genealogy.golden.GoldenFileTestSupport;
import com.emal.genealogy.model.GenealogyDocument;
import com.emal.genealogy.model.Person;
import com.emal.genealogy.repository.GenealogyRepository;
import java.io.IOException;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * Coverage for /api/save-data (DataService, ports save_genealogy_data from
 * app/genealogy_repository.py). There is no Python test for this endpoint
 * at all (grep of tests/ turns up nothing), so unlike every other service
 * test in this codebase there's no tests/golden/*.json fixture to port
 * against - these tests instead pin down save-data's one distinguishing
 * behavior directly: unlike add/update/delete, it's a whole-document
 * overwrite, not a merge, so anything missing from the posted document is
 * dropped rather than left alone.
 */
class DataServiceTest {

    private static final Person ONLY_PERSON =
            new Person("P0001", "Jan", "Kowalski", "M", null, null, List.of(), null, null);

    @Test
    void wholeDocumentOverwriteReplacesEveryCollectionInMemory(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        // Sanity check: the real dataset this sandbox was copied from has more than one person/place/event.
        assertTrue(repository.persons().size() > 1);
        DataService service = new DataService(repository);

        GenealogyDocument replacement =
                new GenealogyDocument(Map.of("P0001", ONLY_PERSON), Map.of(), Map.of(), Map.of(), Map.of());

        SaveDataResult result = service.saveData(replacement);

        assertEquals(new SaveDataResult(), result);
        assertEquals(Map.of("P0001", ONLY_PERSON), repository.persons());
        assertTrue(repository.places().isEmpty());
        assertTrue(repository.events().isEmpty());
        assertTrue(repository.eventParticipations().isEmpty());
    }

    @Test
    void savedDataIsPersistedToDiskAndSurvivesReload(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        DataService service = new DataService(repository);

        GenealogyDocument replacement =
                new GenealogyDocument(Map.of("P0001", ONLY_PERSON), Map.of(), Map.of(), Map.of(), Map.of());
        service.saveData(replacement);

        Path sandboxFile = tempDir.resolve("genealogy_new_model.json");
        GenealogyRepository reloaded = new GenealogyRepository(new DataProperties(sandboxFile.toString()));
        reloaded.load();

        assertEquals(Map.of("P0001", ONLY_PERSON), reloaded.persons());
        assertTrue(reloaded.places().isEmpty());
    }
}
