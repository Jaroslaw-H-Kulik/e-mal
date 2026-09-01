package com.emal.genealogy.web;

import com.emal.genealogy.model.GenealogyDocument;
import com.emal.genealogy.service.DataService;
import com.emal.genealogy.service.SaveDataResult;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/** Thin HTTP layer over DataService - see PersonController's javadoc for the shared conventions this follows. */
@RestController
public class DataController {

    private final DataService dataService;

    public DataController(DataService dataService) {
        this.dataService = dataService;
    }

    @PostMapping("/api/save-data")
    public SaveDataResult saveData(@RequestBody GenealogyDocument document) {
        return dataService.saveData(document);
    }
}
