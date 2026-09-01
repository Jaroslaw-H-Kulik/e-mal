package com.emal.genealogy.service;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.emal.genealogy.golden.DocumentGoldenFileTestSupport;
import com.emal.genealogy.model.Document;
import com.emal.genealogy.model.DocumentPage;
import com.emal.genealogy.repository.DocumentRepository;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * Layer 1 golden-master tests for DocumentService - the Java equivalent of
 * tests/test_documents.py, run directly against the service (no HTTP,
 * matching this project's "service tests carry the golden-parity burden"
 * plan), against the exact same tests/golden/*.json fixtures the Python
 * tests use as the oracle. Every test here adds its own fixture document
 * first rather than anchoring to a real documents.json row - see
 * tests/anchors.py's documents section (Python side) for why.
 */
class DocumentServiceTest {

    private static final IdGenerator ID_GENERATOR = new IdGenerator();
    private static final String NONEXISTENT_DOCUMENT_ID = "D99";
    private static final byte[] FAKE_PAGE_BYTES_1 = "fixture-page-bytes-one".getBytes(StandardCharsets.UTF_8);
    private static final byte[] FAKE_PAGE_BYTES_2 = "fixture-page-bytes-two".getBytes(StandardCharsets.UTF_8);

    private record FixtureDocument(Document document, Map<String, Object> setupDiff) {
    }

    private static DocumentService newService(DocumentRepository repository) {
        return new DocumentService(repository, ID_GENERATOR);
    }

    private static AddDocumentPageRequest pagePayload(byte[] bytes, String ext) {
        return new AddDocumentPageRequest(Base64.getEncoder().encodeToString(bytes), ext);
    }

    private static List<UpdateDocumentPageRequest> pagesAsMaps(Document document) {
        return document.pages().stream()
                .map(page -> new UpdateDocumentPageRequest(page.filename(), page.transcription()))
                .toList();
    }

    /** Mirrors test_documents.py's _add_fixture_document: adds a document via the service itself, returning it plus the setup call's diff (for extraDiffs, never persisted to a fixture). */
    private static FixtureDocument addFixtureDocument(
            DocumentService service, DocumentRepository repository, String name, Integer date,
            List<AddDocumentPageRequest> pages) throws IOException {
        Map<String, Document> before = DocumentGoldenFileTestSupport.snapshot(repository);
        AddDocumentRequest payload = new AddDocumentRequest(name, date, "", List.of(), "", List.of(), pages);

        AddDocumentResult result = service.addDocument(payload);
        Map<String, Document> after = DocumentGoldenFileTestSupport.snapshot(repository);
        AddDocumentResult.Success success = assertInstanceOf(AddDocumentResult.Success.class, result);
        return new FixtureDocument(success.document(), DocumentGoldenFileTestSupport.dictDiff(before, after));
    }

    @Test
    void addDocumentWritesPagesAndCreatesEntry(@TempDir Path tempDir) throws IOException {
        DocumentRepository repository = DocumentGoldenFileTestSupport.freshRepository(tempDir);
        DocumentService service = newService(repository);

        Map<String, Document> before = DocumentGoldenFileTestSupport.snapshot(repository);
        AddDocumentRequest payload = new AddDocumentRequest(
                "Test Document Fixture", 1900, "fixture notes", List.of("test", "fixture"),
                "https://example.invalid/doc", List.of("E0055"),
                List.of(pagePayload(FAKE_PAGE_BYTES_1, "jpg"), pagePayload(FAKE_PAGE_BYTES_2, "png")));

        AddDocumentResult result = service.addDocument(payload);
        Map<String, Document> after = DocumentGoldenFileTestSupport.snapshot(repository);

        DocumentGoldenFileTestSupport.assertMatchesGolden("add_document_creates_pages", result, before, after);

        AddDocumentResult.Success success = assertInstanceOf(AddDocumentResult.Success.class, result);
        Document doc = success.document();
        assertEquals(
                List.of(doc.id() + "-1.jpg", doc.id() + "-2.png"),
                doc.pages().stream().map(DocumentPage::filename).toList());
        assertTrue(doc.pages().stream().allMatch(page -> page.transcription().isEmpty()));
        assertArrayEquals(
                FAKE_PAGE_BYTES_1, Files.readAllBytes(repository.pagesDirectory().resolve(doc.pages().get(0).filename())));
        assertArrayEquals(
                FAKE_PAGE_BYTES_2, Files.readAllBytes(repository.pagesDirectory().resolve(doc.pages().get(1).filename())));
    }

    @Test
    void updateDocumentEditsFieldsAndKeepsPages(@TempDir Path tempDir) throws IOException {
        DocumentRepository repository = DocumentGoldenFileTestSupport.freshRepository(tempDir);
        DocumentService service = newService(repository);

        FixtureDocument setup = addFixtureDocument(
                service, repository, "Before Rename", 1850, List.of(pagePayload(FAKE_PAGE_BYTES_1, "jpg")));
        String docId = setup.document().id();

        Map<String, Document> before = DocumentGoldenFileTestSupport.snapshot(repository);
        UpdateDocumentRequest payload = new UpdateDocumentRequest(
                docId, "After Rename", 1851, "edited", List.of("fixture"),
                "https://example.invalid/renamed", List.of("E0055"), pagesAsMaps(setup.document()));

        UpdateDocumentResult result = service.updateDocument(payload);
        Map<String, Document> after = DocumentGoldenFileTestSupport.snapshot(repository);

        DocumentGoldenFileTestSupport.assertMatchesGolden(
                "update_document_edits_fields", result, before, after, List.of(setup.setupDiff()));

        UpdateDocumentResult.Success success = assertInstanceOf(UpdateDocumentResult.Success.class, result);
        assertEquals("After Rename", success.document().name());
        assertEquals(1851, success.document().date());
        assertEquals(List.of("fixture"), success.document().tags());
        assertEquals(List.of("E0055"), success.document().events());
        assertEquals(setup.document().pages(), success.document().pages());
        assertTrue(Files.exists(repository.pagesDirectory().resolve(setup.document().pages().get(0).filename())));
    }

    @Test
    void deleteDocumentPageRemovesFileKeepsOthers(@TempDir Path tempDir) throws IOException {
        DocumentRepository repository = DocumentGoldenFileTestSupport.freshRepository(tempDir);
        DocumentService service = newService(repository);

        FixtureDocument setup = addFixtureDocument(
                service, repository, "Setup Fixture Document", 1900,
                List.of(pagePayload(FAKE_PAGE_BYTES_1, "jpg"), pagePayload(FAKE_PAGE_BYTES_2, "png")));
        String docId = setup.document().id();
        String keepFilename = setup.document().pages().get(0).filename();
        String dropFilename = setup.document().pages().get(1).filename();
        assertTrue(Files.exists(repository.pagesDirectory().resolve(dropFilename)));

        Map<String, Document> before = DocumentGoldenFileTestSupport.snapshot(repository);
        DeleteDocumentPageResult result =
                service.deleteDocumentPage(new DeleteDocumentPageRequest(docId, dropFilename));
        Map<String, Document> after = DocumentGoldenFileTestSupport.snapshot(repository);

        DocumentGoldenFileTestSupport.assertMatchesGolden(
                "delete_document_page_removes_file", result, before, after, List.of(setup.setupDiff()));

        DeleteDocumentPageResult.Success success = assertInstanceOf(DeleteDocumentPageResult.Success.class, result);
        assertEquals(List.of(keepFilename), success.document().pages().stream().map(DocumentPage::filename).toList());
        assertFalse(Files.exists(repository.pagesDirectory().resolve(dropFilename)));
        assertTrue(Files.exists(repository.pagesDirectory().resolve(keepFilename)));
    }

    @Test
    void deleteDocumentRemovesEntryAndAllPageFiles(@TempDir Path tempDir) throws IOException {
        DocumentRepository repository = DocumentGoldenFileTestSupport.freshRepository(tempDir);
        DocumentService service = newService(repository);

        FixtureDocument setup = addFixtureDocument(
                service, repository, "Setup Fixture Document", 1900,
                List.of(pagePayload(FAKE_PAGE_BYTES_1, "jpg"), pagePayload(FAKE_PAGE_BYTES_2, "png")));
        String docId = setup.document().id();
        List<String> filenames = setup.document().pages().stream().map(DocumentPage::filename).toList();
        for (String filename : filenames) {
            assertTrue(Files.exists(repository.pagesDirectory().resolve(filename)));
        }

        Map<String, Document> before = DocumentGoldenFileTestSupport.snapshot(repository);
        DeleteDocumentResult result = service.deleteDocument(new DeleteDocumentRequest(docId));
        Map<String, Document> after = DocumentGoldenFileTestSupport.snapshot(repository);

        DocumentGoldenFileTestSupport.assertMatchesGolden(
                "delete_document_removes_entry_and_files", result, before, after, List.of(setup.setupDiff()));

        assertEquals(new DeleteDocumentResult.Success(), result);
        assertFalse(after.containsKey(docId));
        for (String filename : filenames) {
            assertFalse(Files.exists(repository.pagesDirectory().resolve(filename)));
        }
    }

    @Test
    void updateNonexistentDocumentFailsCleanly(@TempDir Path tempDir) throws IOException {
        DocumentRepository repository = DocumentGoldenFileTestSupport.freshRepository(tempDir);
        DocumentService service = newService(repository);

        UpdateDocumentResult result = service.updateDocument(
                new UpdateDocumentRequest(NONEXISTENT_DOCUMENT_ID, "x", null, null, null, null, null, null));

        assertEquals(new UpdateDocumentResult.Failure("Document not found"), result);
    }

    @Test
    void deleteNonexistentDocumentFailsCleanly(@TempDir Path tempDir) throws IOException {
        DocumentRepository repository = DocumentGoldenFileTestSupport.freshRepository(tempDir);
        DocumentService service = newService(repository);

        DeleteDocumentResult result = service.deleteDocument(new DeleteDocumentRequest(NONEXISTENT_DOCUMENT_ID));

        assertEquals(new DeleteDocumentResult.Failure("Document not found"), result);
    }

    @Test
    void deletePageOfNonexistentDocumentFailsCleanly(@TempDir Path tempDir) throws IOException {
        DocumentRepository repository = DocumentGoldenFileTestSupport.freshRepository(tempDir);
        DocumentService service = newService(repository);

        DeleteDocumentPageResult result = service.deleteDocumentPage(
                new DeleteDocumentPageRequest(NONEXISTENT_DOCUMENT_ID, "whatever.jpg"));

        assertEquals(new DeleteDocumentPageResult.Failure("Document not found"), result);
    }
}
