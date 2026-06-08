# hash:sha256:bfec4ca9e6c432b0c552406ea657765c417727a10ff724617a2f218d0e9f4579
FROM registry.codeocean.allenneuraldynamics.org/codeocean/ubuntu-desktop-igv-fiji-mambaforge:23.1.0-4-python3.10.12-fiji20231107-1617-firefox120.0-igv2.16.1-guacamole1.5.2-ubuntu22.04

ARG DEBIAN_FRONTEND=noninteractive
ARG AWS_ACCESS_KEY_ID
ARG AWS_DEFAULT_REGION
ARG AWS_SECRET_ACCESS_KEY
ARG CUSTOM_KEY

ARG GIT_ASKPASS
ARG GIT_ACCESS_TOKEN
COPY git-askpass /

RUN mamba install -y \
        openjdk=8 \
        pyimagej==1.5.0 \
        scyjava=1.10.0 \
    && mamba clean -ya

RUN pip3 install -U --no-cache-dir \
    -e git+https://github.com/AllenNeuralDynamics/neuron-tracing-utils@2a4eae62500f3982ff8f42c0aaa56d5e7a9267a7#egg=neuron-tracing-utils

# Pin the JVM-bootstrap stack to the versions this capsule was validated against.
# neuron-tracing-utils depends on `jgo @ git+https://github.com/scijava/jgo` (unpinned),
# which now floats to jgo 3.x -- a pure-Python Maven resolver that ignores ~/.m2/settings.xml,
# over-resolves test-jar artifacts, and fetches a cjdk JRE without the `jar` tool, breaking
# scyjava.start_jvm(). scyjava 1.10.0 + jgo 1.0.6 use the older `mvn`-based
# jgo.resolve_dependencies path (reads settings.xml AND honors scyjava.config repositories),
# which bootstraps Fiji 2.14 correctly. Re-pin jgo AFTER the editable install so it overrides
# the git version (scyjava 1.10.0 is pinned above via conda). jgo 1.0.6 needs only psutil
# (already present), so --no-deps is safe and keeps scyjava untouched.
RUN pip3 install --no-cache-dir --force-reinstall --no-deps 'jgo==1.0.6'

# Bake the Fiji Maven cache into the image so neither build nor runtime depends on the
# rate-limited maven.jzy3d.org server (HTTP 429), which was blocking the run after the
# version pin. Every run otherwise re-downloads the whole Fiji tree, and the small jzy3d
# server throttles the burst. Strategy:
#  (1) Gently fetch ONLY the jzy3d 2.2.1 artifacts (the sole deps that server hosts) one
#      at a time with retry/backoff -- 17 spaced requests, nothing like the burst a full
#      `mvn` resolve makes -- placing them as locally-installed artifacts (no
#      _remote.repositories) so Maven uses them without ever contacting jzy3d.org.
#  (2) Pre-warm the full Fiji/SNT/mobie cache via the real scyjava.start_jvm(): jzy3d
#      comes from local disk, everything else from scijava.public (which does not throttle).
# Result: /root/.m2 + /root/.jgo are baked into the image; runs resolve from local disk
# (no 429 possible) and JVM startup is fast. Validated end-to-end in the pinned image.
RUN base="https://maven.jzy3d.org/releases" \
    && for f in \
        org/jzy3d/jzy3d-all/2.2.1/jzy3d-all-2.2.1.pom \
        org/jzy3d/jzy3d-core-awt/2.2.1/jzy3d-core-awt-2.2.1.jar \
        org/jzy3d/jzy3d-core-awt/2.2.1/jzy3d-core-awt-2.2.1.pom \
        org/jzy3d/jzy3d-core/2.2.1/jzy3d-core-2.2.1-tests.jar \
        org/jzy3d/jzy3d-core/2.2.1/jzy3d-core-2.2.1.jar \
        org/jzy3d/jzy3d-core/2.2.1/jzy3d-core-2.2.1.pom \
        org/jzy3d/jzy3d-jdt-core/2.2.1/jzy3d-jdt-core-2.2.1.jar \
        org/jzy3d/jzy3d-jdt-core/2.2.1/jzy3d-jdt-core-2.2.1.pom \
        org/jzy3d/jzy3d-native-jogl-awt/2.2.1/jzy3d-native-jogl-awt-2.2.1.jar \
        org/jzy3d/jzy3d-native-jogl-awt/2.2.1/jzy3d-native-jogl-awt-2.2.1.pom \
        org/jzy3d/jzy3d-native-jogl-core/2.2.1/jzy3d-native-jogl-core-2.2.1-tests.jar \
        org/jzy3d/jzy3d-native-jogl-core/2.2.1/jzy3d-native-jogl-core-2.2.1.jar \
        org/jzy3d/jzy3d-native-jogl-core/2.2.1/jzy3d-native-jogl-core-2.2.1.pom \
        org/jzy3d/jzy3d-native-jogl-swing/2.2.1/jzy3d-native-jogl-swing-2.2.1.jar \
        org/jzy3d/jzy3d-native-jogl-swing/2.2.1/jzy3d-native-jogl-swing-2.2.1.pom \
        org/jzy3d/jzy3d-tester/2.2.1/jzy3d-tester-2.2.1.jar \
        org/jzy3d/jzy3d-tester/2.2.1/jzy3d-tester-2.2.1.pom \
    ; do \
        dest="/root/.m2/repository/$f"; mkdir -p "$(dirname "$dest")"; \
        echo "jzy3d fetch: $f"; \
        curl -fsSL --retry 6 --retry-delay 15 --retry-all-errors -o "$dest" "$base/$f" \
            || { echo "FAILED to fetch $f"; exit 1; }; \
        [ -s "$dest" ] || { echo "EMPTY artifact $f"; exit 1; }; \
        sleep 2; \
    done

RUN printf '%s\n' \
        '<settings xmlns="http://maven.apache.org/SETTINGS/1.0.0">' \
        '  <profiles><profile><id>jzy3d</id>' \
        '    <repositories><repository><id>jzy3d-releases</id><url>https://maven.jzy3d.org/releases</url>' \
        '      <releases><enabled>true</enabled></releases><snapshots><enabled>false</enabled></snapshots>' \
        '    </repository></repositories>' \
        '  </profile></profiles>' \
        '  <activeProfiles><activeProfile>jzy3d</activeProfile></activeProfiles>' \
        '</settings>' > /root/.m2/settings.xml \
    && JAVA_HOME=/opt/conda/jre python -c "import scyjava.config as c; c.add_repositories({'jzy3d-releases': 'https://maven.jzy3d.org/releases'}); import neuron_tracing_utils.util.java; import scyjava; scyjava.start_jvm(); print('PREWARM_OK')"

# Plotting stack for the vendored single-run figure stage (code/figures/).
# numpy/pandas already come in via neuron-tracing-utils; matplotlib does not.
RUN pip3 install --no-cache-dir matplotlib

COPY postInstall /
# Invoke via `bash` rather than executing directly: Code Ocean's git sync does
# not reliably preserve the file's executable bit, so `RUN /postInstall` fails
# with "Permission denied" (exit 126). `bash /postInstall` is mode-independent.
RUN bash /postInstall
