package com.emal.genealogy.service;

import com.emal.genealogy.model.GenealogyDocument;
import com.emal.genealogy.repository.GenealogyRepository;
import org.springframework.stereotype.Component;

/**
 * Ports save_genealogy_data (app/genealogy_repository.py): a whole-document
 * overwrite, not a partial update - unlike every add/update/delete
 * endpoint, this replaces persons/places/events/event_participations/
 * metadata wholesale with whatever the request body sent, no validation. In
 * Python this is stateless (load_data/save_data reread the file around
 * every call); in Java the repository already holds the document in
 * memory, so this just swaps every collection and persists.
 */
@Component
public class DataService {

    private final GenealogyRepository repository;

    public DataService(GenealogyRepository repository) {
        this.repository = repository;
    }

    public SaveDataResult saveData(GenealogyDocument document) {
        repository.replace(document);
        repository.save();
        return new SaveDataResult();
    }
}
