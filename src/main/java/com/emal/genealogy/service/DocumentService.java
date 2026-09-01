package com.emal.genealogy.service;

import com.emal.genealogy.model.Document;
import com.emal.genealogy.model.DocumentPage;
import com.emal.genealogy.repository.DocumentRepository;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.NoSuchElementException;
import org.springframework.stereotype.Component;

/**
 * Ports server.py's add_document/update_document/delete_document/
 * delete_document_page - unlike every other service in this codebase,
 * these also perform real file I/O (decoding/writing/deleting page-image
 * files under data/documents/), not just JSON-map mutation, so their
 * try/catch also has to guard against checked {@link IOException} the way
 * Python's blanket {@code except Exception} does for free.
 */
@Component
public class DocumentService {

    private final DocumentRepository repository;
    private final IdGenerator idGenerator;

    public DocumentService(DocumentRepository repository, IdGenerator idGenerator) {
        this.repository = repository;
        this.idGenerator = idGenerator;
    }

    /**
     * Ports add_document: decodes and writes each page's base64 payload to
     * {@code data/documents/<new_id>-<n>.<ext>} (1-indexed, ext defaults to
     * "jpg" and is lowercased, exactly like Python), then stores the
     * canonical 8-field document record with every page's transcription
     * starting empty.
     */
    public AddDocumentResult addDocument(AddDocumentRequest data) {
        try {
            Map<String, Document> documents = repository.documents();
            String docId = idGenerator.nextDocumentId(documents);
            Path pagesDirectory = repository.pagesDirectory();

            List<DocumentPage> pages = new ArrayList<>();
            int pageNumber = 1;
            for (AddDocumentPageRequest pageData : data.pages()) {
                String ext = pageData.ext().toLowerCase();
                String filename = docId + "-" + pageNumber + "." + ext;
                byte[] bytes = Base64.getDecoder().decode(requireField("data", pageData.data()));
                Files.write(pagesDirectory.resolve(filename), bytes);
                pages.add(new DocumentPage(filename, "", null));
                pageNumber++;
            }

            Document document = new Document(
                    docId, data.name(), data.date(), data.notes(), data.tags(), data.link(), data.events(),
                    pages, null);
            documents.put(docId, document);
            repository.save();

            return new AddDocumentResult.Success(document);
        } catch (IOException | RuntimeException e) {
            return new AddDocumentResult.Failure(e.getMessage());
        }
    }

    /**
     * Ports update_document: overwrites every field of the existing document
     * with whatever the request sent, including {@code pages} being
     * replaced wholesale (the real client always round-trips the full
     * pages array on every save - see document-manager.js's
     * saveEditDocument/linkDocumentToEvent/unlinkDocumentFromEvent, all of
     * which always send the complete field set - see UpdateDocumentRequest's
     * javadoc for why this no longer replicates the old per-key partial
     * update). Never touches files on disk - page-file writes only happen
     * via add-document/delete-document-page.
     */
    public UpdateDocumentResult updateDocument(UpdateDocumentRequest data) {
        try {
            Map<String, Document> documents = repository.documents();
            String docId = data.id();
            if (docId == null || !documents.containsKey(docId)) {
                return new UpdateDocumentResult.Failure("Document not found");
            }

            Document updated = new Document(
                    docId, data.name(), data.date(), data.notes(), data.tags(), data.link(), data.events(),
                    toDocumentPages(data.pages()), documents.get(docId).extra());
            documents.put(docId, updated);
            repository.save();

            return new UpdateDocumentResult.Success(updated);
        } catch (RuntimeException e) {
            return new UpdateDocumentResult.Failure(e.getMessage());
        }
    }

    /**
     * Ports delete_document: removes every one of the document's page
     * files from disk (silently skipping ones already missing, matching
     * Python's {@code if os.path.exists(filepath): os.remove(filepath)}),
     * then the document entry itself. Response carries no "document" key
     * on success, unlike every other document result - matches Python's
     * {@code {'success': True}} exactly.
     */
    public DeleteDocumentResult deleteDocument(DeleteDocumentRequest data) {
        try {
            Map<String, Document> documents = repository.documents();
            String docId = data.id();
            if (docId == null || !documents.containsKey(docId)) {
                return new DeleteDocumentResult.Failure("Document not found");
            }

            Path pagesDirectory = repository.pagesDirectory();
            for (DocumentPage page : documents.get(docId).pages()) {
                Files.deleteIfExists(pagesDirectory.resolve(page.filename()));
            }
            documents.remove(docId);
            repository.save();

            return new DeleteDocumentResult.Success();
        } catch (IOException | RuntimeException e) {
            return new DeleteDocumentResult.Failure(e.getMessage());
        }
    }

    /**
     * Ports delete_document_page: removes one page's file from disk
     * (silently skipping if already missing) and drops it from the
     * document's pages list, leaving every other field untouched.
     */
    public DeleteDocumentPageResult deleteDocumentPage(DeleteDocumentPageRequest data) {
        try {
            Map<String, Document> documents = repository.documents();
            String docId = data.docId();
            String filename = data.filename();
            if (docId == null || !documents.containsKey(docId)) {
                return new DeleteDocumentPageResult.Failure("Document not found");
            }

            Path pagesDirectory = repository.pagesDirectory();
            Files.deleteIfExists(pagesDirectory.resolve(filename));

            Document existing = documents.get(docId);
            List<DocumentPage> remainingPages = existing.pages().stream()
                    .filter(page -> !page.filename().equals(filename))
                    .toList();
            Document updated = new Document(
                    existing.id(), existing.name(), existing.date(), existing.notes(), existing.tags(),
                    existing.link(), existing.events(), remainingPages, existing.extra());
            documents.put(docId, updated);
            repository.save();

            return new DeleteDocumentPageResult.Success(updated);
        } catch (IOException | RuntimeException e) {
            return new DeleteDocumentPageResult.Failure(e.getMessage());
        }
    }

    private static List<DocumentPage> toDocumentPages(List<UpdateDocumentPageRequest> pages) {
        return pages.stream()
                .map(page -> new DocumentPage(page.filename(), page.transcription(), null))
                .toList();
    }

    /** Mirrors RequestValues.requireString's Python-KeyError-shaped message for a field that's null (JSON key omitted). */
    private static String requireField(String key, String value) {
        if (value == null) {
            throw new NoSuchElementException("'" + key + "'");
        }
        return value;
    }
}
