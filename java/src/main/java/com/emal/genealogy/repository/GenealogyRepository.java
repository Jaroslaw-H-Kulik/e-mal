package com.emal.genealogy.repository;

import com.emal.genealogy.config.DataProperties;
import com.emal.genealogy.model.Event;
import com.emal.genealogy.model.EventParticipation;
import com.emal.genealogy.model.GenealogyDocument;
import com.emal.genealogy.model.Person;
import com.emal.genealogy.model.Place;
import com.emal.genealogy.model.serialization.GenealogyJsonMapper;
import jakarta.annotation.PostConstruct;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.stereotype.Component;
import tools.jackson.databind.json.JsonMapper;

/**
 * Loads data/genealogy_new_model.json into memory on startup and can write
 * it back out. No business logic here - see JAVA_MIGRATION.md's migration
 * order for where add/update/delete logic lands (service/ layer, ported
 * from app/genealogy_repository.py's GenealogyRepository).
 */
@Component
public class GenealogyRepository {

    private final JsonMapper objectMapper = GenealogyJsonMapper.create();
    private final Path dataFile;

    private Map<String, Person> persons;
    private Map<String, Place> places;
    private Map<String, Event> events;
    private Map<String, EventParticipation> eventParticipations;
    private Map<String, Object> metadata;

    public GenealogyRepository(DataProperties dataProperties) {
        this.dataFile = Path.of(dataProperties.file());
    }

    @PostConstruct
    public void load() {
        loadFrom(dataFile);
    }

    void loadFrom(Path path) {
        GenealogyDocument document = objectMapper.readValue(path.toFile(), GenealogyDocument.class);
        this.persons = new LinkedHashMap<>(document.persons());
        this.places = new LinkedHashMap<>(document.places());
        this.events = new LinkedHashMap<>(document.events());
        this.eventParticipations = new LinkedHashMap<>(document.eventParticipations());
        this.metadata = new LinkedHashMap<>(document.metadata());
    }

    public void save() {
        saveTo(dataFile);
    }

    void saveTo(Path path) {
        GenealogyDocument document =
                new GenealogyDocument(persons, places, events, eventParticipations, metadata);
        objectMapper.writeValue(path.toFile(), document);
    }

    public Map<String, Person> persons() {
        return persons;
    }

    public Map<String, Place> places() {
        return places;
    }

    public Map<String, Event> events() {
        return events;
    }

    public Map<String, EventParticipation> eventParticipations() {
        return eventParticipations;
    }

    public Map<String, Object> metadata() {
        return metadata;
    }
}
