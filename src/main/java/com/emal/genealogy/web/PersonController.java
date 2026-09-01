package com.emal.genealogy.web;

import com.emal.genealogy.service.AddPersonRequest;
import com.emal.genealogy.service.AddPersonResult;
import com.emal.genealogy.service.DeletePersonRequest;
import com.emal.genealogy.service.DeletePersonResult;
import com.emal.genealogy.service.PersonService;
import com.emal.genealogy.service.UpdatePersonRequest;
import com.emal.genealogy.service.UpdatePersonResult;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/**
 * Thin HTTP layer over PersonService - delegates and returns whichever
 * result variant the service produced as-is. Spring's snake_case-configured
 * Jackson mapper (config/JacksonConfig) both binds request bodies
 * (AddPersonRequest's given_name etc.) and serializes responses into the
 * same JSON shape server.py's POST endpoints return, always as HTTP 200 -
 * server.py never uses HTTP status codes to signal failures, only the
 * "success" field in the body. Every endpoint in this codebase has a typed
 * request body.
 */
@RestController
public class PersonController {

    private final PersonService personService;

    public PersonController(PersonService personService) {
        this.personService = personService;
    }

    @PostMapping("/api/add-person")
    public AddPersonResult addPerson(@RequestBody AddPersonRequest personData) {
        return personService.addPerson(personData);
    }

    @PostMapping("/api/update-person")
    public UpdatePersonResult updatePerson(@RequestBody UpdatePersonRequest personData) {
        return personService.updatePerson(personData);
    }

    @PostMapping("/api/delete-person")
    public DeletePersonResult deletePerson(@RequestBody DeletePersonRequest requestData) {
        return personService.deletePerson(requestData);
    }
}
