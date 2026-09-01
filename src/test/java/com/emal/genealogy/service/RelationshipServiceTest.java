package com.emal.genealogy.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertNull;

import com.emal.genealogy.golden.GoldenFileTestSupport;
import com.emal.genealogy.golden.GoldenFileTestSupport.EntitySnapshot;
import com.emal.genealogy.repository.GenealogyRepository;
import java.io.IOException;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * Layer 1 golden-master tests for RelationshipService.addRelationship - the
 * Java equivalent of tests/test_add_relationship.py, run directly against
 * the service, against the exact same tests/golden/add_relationship_*.json
 * fixtures the Python tests use as the oracle. See PersonServiceTest for
 * the harness pattern.
 */
class RelationshipServiceTest {

    // tests/anchors.py constants this file's scenarios pin against.
    private static final String NO_BIRTH_EVENT_CHILD = "P0012";
    private static final String UNRELATED_FEMALE = "P0033";
    private static final String HAS_BIRTH_EVENT_CHILD = "P0800";
    private static final String HAS_BIRTH_EVENT_CHILD_EVENT = "E1746";
    private static final String UNRELATED_MALE = "P0038";
    private static final String SPOUSE_BASE = "P0001";
    private static final String SPOUSE_TARGET = "P0007";
    private static final String GODPARENT_CHILD = "P0114";
    private static final String GODPARENT_CHILD_EVENT = "E0583";
    private static final String NEW_GODPARENT = "P0042";

    private static RelationshipService newService(GenealogyRepository repository) {
        IdGenerator idGenerator = new IdGenerator();
        EventLookup eventLookup = new EventLookup();
        ParentMarriageService parentMarriageService = new ParentMarriageService(idGenerator, eventLookup);
        return new RelationshipService(repository, idGenerator, eventLookup, parentMarriageService);
    }

    private static AddRelationshipRequest payload(String basePersonId, String targetPersonId, String relType, String role) {
        return new AddRelationshipRequest(basePersonId, targetPersonId, relType, role);
    }

    @Test
    void parentCreatesBirthEventWhenNoneExists(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        RelationshipService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        AddRelationshipResult result = service.addRelationship(
                payload(NO_BIRTH_EVENT_CHILD, UNRELATED_FEMALE, "parent", "mother"));
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("add_relationship_parent_new_birth_event", result, before, after);

        AddRelationshipResult.Success success = assertInstanceOf(AddRelationshipResult.Success.class, result);
        assertEquals(true, success.success());
        assertNull(success.updatedEvent());
    }

    @Test
    void parentReusesExistingBirthEvent(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        RelationshipService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        AddRelationshipResult result = service.addRelationship(
                payload(HAS_BIRTH_EVENT_CHILD, UNRELATED_MALE, "parent", "father"));
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("add_relationship_parent_reuses_birth_event", result, before, after);

        AddRelationshipResult.Success success = assertInstanceOf(AddRelationshipResult.Success.class, result);
        assertNull(success.createdEvent());
        assertEquals(HAS_BIRTH_EVENT_CHILD_EVENT, success.updatedEvent());
    }

    @Test
    void spouseCreatesMarriageEvent(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        RelationshipService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        AddRelationshipResult result = service.addRelationship(
                payload(SPOUSE_BASE, SPOUSE_TARGET, "spouse", "spouse"));
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("add_relationship_spouse_new_marriage_event", result, before, after);

        AddRelationshipResult.Success success = assertInstanceOf(AddRelationshipResult.Success.class, result);
        assertNull(success.updatedEvent());
    }

    @Test
    void godparentReusesExistingBirthEvent(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        RelationshipService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        AddRelationshipResult result = service.addRelationship(
                payload(GODPARENT_CHILD, NEW_GODPARENT, "godparent", "godparent"));
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        GoldenFileTestSupport.assertMatchesGolden("add_relationship_godparent_reuses_birth_event", result, before, after);

        AddRelationshipResult.Success success = assertInstanceOf(AddRelationshipResult.Success.class, result);
        assertNull(success.createdEvent());
        assertEquals(GODPARENT_CHILD_EVENT, success.updatedEvent());
    }

    @Test
    void missingRoleKeyFailsCleanly(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        RelationshipService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        // 'role' intentionally null (JSON key omitted)
        AddRelationshipRequest payload = new AddRelationshipRequest(
                NO_BIRTH_EVENT_CHILD, UNRELATED_FEMALE, "parent", null);

        AddRelationshipResult result = service.addRelationship(payload);
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        assertEquals(new AddRelationshipResult.Failure("'role'"), result);
        assertEquals(before, after);
    }

    @Test
    void unknownRelationshipTypeFailsCleanly(@TempDir Path tempDir) throws IOException {
        GenealogyRepository repository = GoldenFileTestSupport.freshRepository(tempDir);
        RelationshipService service = newService(repository);

        EntitySnapshot before = GoldenFileTestSupport.snapshot(repository);
        AddRelationshipResult result = service.addRelationship(
                payload(NO_BIRTH_EVENT_CHILD, UNRELATED_FEMALE, "sibling", "sibling"));
        EntitySnapshot after = GoldenFileTestSupport.snapshot(repository);

        assertEquals(new AddRelationshipResult.Failure("Unknown relationship type: sibling"), result);
        assertEquals(before, after);
    }
}
