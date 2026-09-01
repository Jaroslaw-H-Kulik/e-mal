package com.emal.genealogy.repository;

import com.emal.genealogy.config.DocumentDataProperties;
import com.emal.genealogy.model.Document;
import com.emal.genealogy.model.serialization.GenealogyJsonMapper;
import jakarta.annotation.PostConstruct;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.stereotype.Component;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

/**
 * Loads data/documents.json into memory on startup and can write it back
 * out - the Document-family equivalent of GenealogyRepository, kept
 * entirely separate since documents.json is its own file with its own flat
 * {@code {doc_id: document}} shape (no wrapper record needed, unlike
 * GenealogyDocument). Reuses GenealogyJsonMapper.create() as-is for the
 * CRLF/snake_case/indent-2 formatting - it's generic, not tied to
 * GenealogyDocument.
 *
 * <p>Also owns the page-image directory (data/documents/, the sibling of
 * documents.json) - {@link #pagesDirectory()} lazily ensures it exists on
 * every call, mirroring server.py's {@code _documents_dir()}
 * ({@code os.makedirs(d, exist_ok=True)} on every access, not just once at
 * startup).
 */
@Component
public class DocumentRepository {

    private final JsonMapper objectMapper = GenealogyJsonMapper.create();
    private final Path dataFile;
    private final Path pagesDirectory;

    private Map<String, Document> documents;

    public DocumentRepository(DocumentDataProperties dataProperties) {
        this.dataFile = Path.of(dataProperties.file());
        this.pagesDirectory = this.dataFile.toAbsolutePath().normalize().getParent().resolve("documents");
    }

    @PostConstruct
    public void load() {
        loadFrom(dataFile);
    }

    void loadFrom(Path path) {
        Map<String, Document> loaded =
                objectMapper.readValue(path.toFile(), new TypeReference<Map<String, Document>>() {});
        this.documents = new LinkedHashMap<>(loaded);
    }

    public void save() {
        saveTo(dataFile);
    }

    void saveTo(Path path) {
        objectMapper.writeValue(path.toFile(), documents);
    }

    public Map<String, Document> documents() {
        return documents;
    }

    public Path pagesDirectory() throws IOException {
        Files.createDirectories(pagesDirectory);
        return pagesDirectory;
    }
}
