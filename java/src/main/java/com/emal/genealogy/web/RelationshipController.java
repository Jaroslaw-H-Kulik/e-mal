package com.emal.genealogy.web;

import com.emal.genealogy.service.AddRelationshipResult;
import com.emal.genealogy.service.RelationshipService;
import java.util.Map;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/** Thin HTTP layer over RelationshipService - see PersonController's javadoc for the same shape/status-code rationale. */
@RestController
public class RelationshipController {

    private final RelationshipService relationshipService;

    public RelationshipController(RelationshipService relationshipService) {
        this.relationshipService = relationshipService;
    }

    @PostMapping("/api/add-relationship")
    public AddRelationshipResult addRelationship(@RequestBody Map<String, Object> relData) {
        return relationshipService.addRelationship(relData);
    }
}
