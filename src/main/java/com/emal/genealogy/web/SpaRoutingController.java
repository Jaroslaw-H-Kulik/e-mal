package com.emal.genealogy.web;

import com.emal.genealogy.config.FrontendProperties;
import jakarta.servlet.http.HttpServletRequest;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Mirrors server.py's do_GET SPA-routing special-case: a browser
 * navigating directly to a client-side-router URL - /person/&lt;id&gt;,
 * /document/&lt;id&gt;, or /events - must still get index.html (not
 * Spring's default 404 for an unmapped path) so the frontend's own JS
 * router (app.js/document-manager.js) can take over from there, exactly
 * like {@code self.path.startswith('/person/') or
 * self.path.startswith('/document/') or self.path == '/events'} does in
 * server.py. Bare /person and bare /document (no trailing segment) are
 * intentionally excluded (fall through to a 404, matching what Python's
 * static-file fallback does for them too) - mirroring Python's
 * startswith('/person/')/startswith('/document/') requiring the slash.
 * The mappings themselves are "/person/**"/"/document/**", which Spring's
 * default PathPatternParser matches against the bare paths as well
 * (unlike Python's literal startswith check), so those exclusions are
 * enforced explicitly in the handler rather than left to the mapping.
 *
 * Reads index.html from disk on every request rather than caching it, the
 * same as Spring's static resource handler (and Python's
 * SimpleHTTPRequestHandler) already does for every other file under
 * web/ - keeps hot-editing index.html during development working the same
 * way it does for every other frontend file.
 */
@RestController
public class SpaRoutingController {

    private final Path indexHtml;

    public SpaRoutingController(FrontendProperties frontendProperties) {
        this.indexHtml = Path.of(frontendProperties.root()).resolve("index.html");
    }

    @GetMapping({"/events", "/person/**", "/document/**"})
    public ResponseEntity<byte[]> spaFallback(HttpServletRequest request) throws IOException {
        String requestUri = request.getRequestURI();
        if ("/person".equals(requestUri) || "/document".equals(requestUri)) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok().contentType(MediaType.TEXT_HTML).body(Files.readAllBytes(indexHtml));
    }
}
