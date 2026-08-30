package com.emal.genealogy.config;

import java.nio.file.Path;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * Serves data/ and web/ under their own explicit /data/** and /web/**
 * URL prefixes, mirroring server.py's do_GET routing precisely - it
 * deliberately leaves both prefixes untouched (`elif not
 * self.path.startswith('/web/') and not self.path.startswith('/data/')`)
 * so the base SimpleHTTPRequestHandler serves them as real subfolders of
 * the process's working directory (repo root).
 *
 * <p><b>/data/**</b>: web/app.js's entire read path for the genealogy
 * model depends on this - it never calls an /api/* endpoint to read data,
 * only to write it: loadData() fetches /data/genealogy_new_model.json and
 * /data/documents.json on every page load, and
 * document-manager.js's scanned page thumbnails load straight from
 * /data/documents/&lt;filename&gt; as plain &lt;img src&gt; static
 * requests.
 *
 * <p><b>/web/**</b>: every asset web/index.html itself references uses
 * this exact absolute prefix - {@code <link href="/web/style.css">} and
 * five {@code <script src="/web/*.js">} tags. The default
 * spring.web.resources.static-locations config (file:../web/, mapped
 * under the bare "/**" pattern - kept below for
 * WelcomePageHandlerMapping to find index.html at "/") does NOT cover
 * this: a request for "/web/style.css" resolves against that mapping as
 * "../web/web/style.css" (a doubled "web" segment) and 404s - which is
 * exactly what happened the first time the real UI was opened in a
 * browser against the Java backend (page loads, but unstyled with no JS:
 * every /web/* asset silently 404ing, since nothing before that point had
 * driven a real browser load - only curl hits against specific known-good
 * paths).
 *
 * <p>Both locations are derived from existing config
 * (DataProperties.file(), FrontendProperties.root()) rather than new
 * config keys, so they always serve whichever directories the app was
 * actually started against - including sandboxed overrides during a
 * smoke test - with no risk of drifting out of sync.
 */
@Configuration
public class StaticResourceConfig implements WebMvcConfigurer {

    private final String dataDirectoryLocation;
    private final String webRootLocation;

    public StaticResourceConfig(DataProperties dataProperties, FrontendProperties frontendProperties) {
        Path dataDir = Path.of(dataProperties.file()).toAbsolutePath().normalize().getParent();
        this.dataDirectoryLocation = dataDir.toUri().toString();

        Path webDir = Path.of(frontendProperties.root()).toAbsolutePath().normalize();
        this.webRootLocation = webDir.toUri().toString();
    }

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        registry.addResourceHandler("/data/**").addResourceLocations(dataDirectoryLocation);
        registry.addResourceHandler("/web/**").addResourceLocations(webRootLocation);
    }
}
