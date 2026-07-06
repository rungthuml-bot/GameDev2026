/*! coi-serviceworker v0.1.7 - Guido Zuidhof and contributors, licensed under MIT */
let coepCredentialless = false;
if (typeof window === 'undefined') {
    self.addEventListener("install", () => self.skipWaiting());
    self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

    self.addEventListener("message", (ev) => {
        if (ev.data && ev.data.type === "deregister") {
            self.registration
                .unregister()
                .then(() => {
                    return self.clients.matchAll();
                })
                .then((clients) => {
                    clients.forEach((client) => client.navigate(client.url));
                });
        }
    });

    self.addEventListener("fetch", function (event) {
        const r = event.request;
        if (r.cache === "only-if-cached" && r.mode !== "same-origin") {
            return;
        }

        const request = (coepCredentialless && r.mode === "no-cors")
            ? new Request(r, { credentials: "omit" })
            : r;

        event.respondWith(
            fetch(request)
                .then((response) => {
                    if (response.status === 0) {
                        return response;
                    }

                    const newHeaders = new Headers(response.headers);
                    newHeaders.set("Cross-Origin-Embedder-Policy",
                        coepCredentialless ? "credentialless" : "require-corp"
                    );
                    if (!coepCredentialless) {
                        newHeaders.set("Cross-Origin-Resource-Policy", "cross-origin");
                    }
                    newHeaders.set("Cross-Origin-Opener-Policy", "same-origin");

                    return new Response(response.body, {
                        status: response.status,
                        statusText: response.statusText,
                        headers: newHeaders,
                    });
                })
                .catch((e) => console.error(e))
        );
    });

} else {
    (() => {
        const reloadedByCOI = window.sessionStorage.getItem("coiReloadedByCOI");
        window.sessionStorage.removeItem("coiReloadedByCOI");

        const coiError = () => {
            console.log(
                "[coi] Could not register coi service worker. Is your serving from a secure (HTTPS) context?"
            );
        };

        if (window.crossOriginIsolated !== false || reloadedByCOI === "true") {
            return;
        }

        if (!window.isSecureContext) {
            coiError();
            return;
        }

        const coi = {
            shouldRegister: () => true,
            shouldDeregister: () => false,
            coepCredentialless: () => (typeof window !== 'undefined' ? window.chrome !== undefined : true),
            coepDegrade: () => true,
            doReload: () => window.location.reload(),
            quiet: false,
            ...window.cpiConfig,
        };

        if (!coi.shouldRegister()) {
            return;
        }

        if (!window.crossOriginIsolated) {
            if (!coi.quiet) {
                console.log("[coi] page is not cross-origin isolated, registering service worker...");
            }

            const src = window.document.currentScript.src;
            const swPath = src ? new URL(src).pathname : "/coi-serviceworker.js";

            navigator.serviceWorker
                .register(swPath)
                .then(
                    (registration) => {
                        if (!coi.quiet) {
                            console.log("[coi] Service worker registered, reloading page to enable cross-origin isolation...");
                        }
                        registration.addEventListener("updatefound", () => {
                            if (!coi.quiet) {
                                console.log("[coi] Reloading page to make use of updated service worker.");
                            }
                            registration.installing.addEventListener("statechange", () => {
                                if (registration.installing && registration.installing.state === "activated") {
                                    window.sessionStorage.setItem("coiReloadedByCOI", "true");
                                    coi.doReload();
                                }
                            });
                        });

                        if (registration.active && !navigator.serviceWorker.controller) {
                            window.sessionStorage.setItem("coiReloadedByCOI", "true");
                            coi.doReload();
                        }
                    },
                    coiError
                );
        }
    })();
}
