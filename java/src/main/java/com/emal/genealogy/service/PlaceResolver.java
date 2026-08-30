package com.emal.genealogy.service;

import com.emal.genealogy.model.Place;
import java.util.Map;
import java.util.Objects;
import org.springframework.stereotype.Component;

/**
 * Ports GenealogyRepository.resolve_place/handle_place
 * (app/genealogy_repository.py). resolve_place has two independently-
 * duplicated matching rules depending on whether a house number is
 * meaningful for the caller (see its Python docstring) - preserved as two
 * separate Java methods rather than reconciled, since changing either
 * would change which existing places get reused:
 *
 * - {@link #resolveByNameOnly}: house_number=None branch - name-only,
 *   case-insensitive match, used directly by add-person/update-person.
 * - {@link #resolveByNameAndHouseNumber}: house_number-given branch -
 *   name (case-sensitive) AND house_number match, reached via
 *   {@link #handlePlace} for add-event/update-event.
 *
 * Creates places with the full canonical field set - see
 * JAVA_MIGRATION.md's `resolve_place` Phase 0 addenda for why this had to
 * be fixed in the Python reference first (both branches).
 */
@Component
public class PlaceResolver {

    private final IdGenerator idGenerator;

    public PlaceResolver(IdGenerator idGenerator) {
        this.idGenerator = idGenerator;
    }

    public String resolveByNameOnly(Map<String, Place> places, String placeName) {
        for (Place place : places.values()) {
            if (place.name() != null && place.name().equalsIgnoreCase(placeName)) {
                return place.id();
            }
        }
        String newId = idGenerator.nextPlaceId(places);
        places.put(newId, new Place(newId, placeName, null, null, "settlement", null));
        return newId;
    }

    public String resolveByNameAndHouseNumber(Map<String, Place> places, String placeName, String houseNumber) {
        for (Place place : places.values()) {
            if (Objects.equals(place.name(), placeName) && Objects.equals(place.houseNumber(), houseNumber)) {
                return place.id();
            }
        }
        String newId = idGenerator.nextPlaceId(places);
        places.put(newId, new Place(newId, placeName, null, houseNumber, null, null));
        return newId;
    }

    /**
     * Ports handle_place: no place_name -> null. Otherwise resolves via
     * house_number if the request supplied a house_number key at all
     * (even an explicit null - matching resolve_place's own
     * house_number=None branch selection), else via name-only with an
     * empty-string house_number default (event_data.get('house_number',
     * '') in Python), matching the house_number-given branch's
     * empty-string comparison for a request that omits house_number
     * entirely.
     */
    public String handlePlace(Map<String, Place> places, Map<String, Object> eventData) {
        String placeName = RequestValues.truthyString(eventData, "place_name");
        if (placeName == null) {
            return null;
        }
        if (!eventData.containsKey("house_number")) {
            return resolveByNameAndHouseNumber(places, placeName, "");
        }
        String houseNumber = RequestValues.asStringOrNull(eventData.get("house_number"));
        if (houseNumber == null) {
            return resolveByNameOnly(places, placeName);
        }
        return resolveByNameAndHouseNumber(places, placeName, houseNumber);
    }
}
