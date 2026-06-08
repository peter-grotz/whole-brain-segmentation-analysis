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
    && mamba clean -ya

RUN pip3 install -U --no-cache-dir \
    -e git+https://github.com/AllenNeuralDynamics/neuron-tracing-utils@2a4eae62500f3982ff8f42c0aaa56d5e7a9267a7#egg=neuron-tracing-utils

# Plotting stack for the vendored single-run figure stage (code/figures/).
# numpy/pandas already come in via neuron-tracing-utils; matplotlib does not.
RUN pip3 install --no-cache-dir matplotlib

COPY postInstall /
# Invoke via `bash` rather than executing directly: Code Ocean's git sync does
# not reliably preserve the file's executable bit, so `RUN /postInstall` fails
# with "Permission denied" (exit 126). `bash /postInstall` is mode-independent.
RUN bash /postInstall
