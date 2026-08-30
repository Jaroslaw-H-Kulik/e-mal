package com.emal.genealogy.repository;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;

import com.emal.genealogy.config.DataProperties;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * JAVA_MIGRATION.md step 1 exit criterion: a no-op load then save of the
 * real data file must be byte-identical to the source, proving the model +
 * repository are lossless before any service logic is layered on.
 */
class GenealogyRepositoryRoundTripTest {

    private static final Path REAL_DATA_FILE = Path.of("../data/genealogy_new_model.json");

    @Test
    void loadThenSaveIsByteIdenticalToSource(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = new GenealogyRepository(new DataProperties(REAL_DATA_FILE.toString()));
        repository.loadFrom(REAL_DATA_FILE);

        Path output = tempDir.resolve("roundtrip.json");
        repository.saveTo(output);

        byte[] original = Files.readAllBytes(REAL_DATA_FILE);
        byte[] roundTripped = Files.readAllBytes(output);
        assertArrayEquals(original, roundTripped);
    }
}
