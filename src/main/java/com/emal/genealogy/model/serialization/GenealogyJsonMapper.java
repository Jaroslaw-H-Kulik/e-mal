package com.emal.genealogy.model.serialization;

import tools.jackson.core.util.DefaultIndenter;
import tools.jackson.core.util.DefaultPrettyPrinter;
import tools.jackson.core.util.Separators;
import tools.jackson.databind.PropertyNamingStrategies;
import tools.jackson.databind.SerializationFeature;
import tools.jackson.databind.json.JsonMapper;

/**
 * Builds the ObjectMapper used to read/write data/genealogy_new_model.json.
 * Formatting (2-space indent, "\n" line endings, ": " colon spacing, no
 * space before commas) is matched byte-for-byte against Python's
 * json.dump(data, f, ensure_ascii=False, indent=2) so a no-op load-then-save
 * round trip is identical to the source file. See JAVA_MIGRATION.md, step 1
 * exit criterion.
 */
public final class GenealogyJsonMapper {

    private GenealogyJsonMapper() {
    }

    public static JsonMapper create() {
        // Matches Python's json.dump(data, f, ensure_ascii=False, indent=2) as
        // written by open(file, "w") on Windows, which translates "\n" to the
        // platform line separator ("\r\n") - the source data file is CRLF.
        DefaultIndenter indenter = new DefaultIndenter("  ", "\r\n");
        Separators separators = Separators.createDefaultInstance()
                .withObjectNameValueSpacing(Separators.Spacing.AFTER)
                .withObjectEmptySeparator("")
                .withArrayEmptySeparator("");
        DefaultPrettyPrinter prettyPrinter = new DefaultPrettyPrinter(separators)
                .withObjectIndenter(indenter)
                .withArrayIndenter(indenter);

        return JsonMapper.builder()
                .propertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE)
                .defaultPrettyPrinter(prettyPrinter)
                .enable(SerializationFeature.INDENT_OUTPUT)
                .build();
    }
}
