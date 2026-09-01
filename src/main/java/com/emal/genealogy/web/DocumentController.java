package com.emal.genealogy.web;

import com.emal.genealogy.service.AddDocumentRequest;
import com.emal.genealogy.service.AddDocumentResult;
import com.emal.genealogy.service.DeleteDocumentPageRequest;
import com.emal.genealogy.service.DeleteDocumentPageResult;
import com.emal.genealogy.service.DeleteDocumentRequest;
import com.emal.genealogy.service.DeleteDocumentResult;
import com.emal.genealogy.service.DocumentService;
import com.emal.genealogy.service.UpdateDocumentRequest;
import com.emal.genealogy.service.UpdateDocumentResult;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/** Thin HTTP layer over DocumentService - see PersonController's javadoc for the same shape/status-code rationale. */
@RestController
public class DocumentController {

    private final DocumentService documentService;

    public DocumentController(DocumentService documentService) {
        this.documentService = documentService;
    }

    @PostMapping("/api/add-document")
    public AddDocumentResult addDocument(@RequestBody AddDocumentRequest data) {
        return documentService.addDocument(data);
    }

    @PostMapping("/api/update-document")
    public UpdateDocumentResult updateDocument(@RequestBody UpdateDocumentRequest data) {
        return documentService.updateDocument(data);
    }

    @PostMapping("/api/delete-document")
    public DeleteDocumentResult deleteDocument(@RequestBody DeleteDocumentRequest data) {
        return documentService.deleteDocument(data);
    }

    @PostMapping("/api/delete-document-page")
    public DeleteDocumentPageResult deleteDocumentPage(@RequestBody DeleteDocumentPageRequest data) {
        return documentService.deleteDocumentPage(data);
    }
}
