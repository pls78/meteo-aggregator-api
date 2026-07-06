# deployment Specification

## Purpose

Package and run the aggregator API as a portable, low-cost service. The API is
stateless and keyless, so it is deployed as a single container that scales to
zero when idle (e.g. Google Cloud Run).

## Requirements

### Requirement: Containerized service

The API SHALL be buildable and runnable as a container from a `Dockerfile` in the
repository root, with no build-time secrets or credentials.

#### Scenario: Image builds and serves

- **WHEN** the container image is built from the repository `Dockerfile` and run
- **THEN** the API starts and serves requests over HTTP

### Requirement: Configurable listen port

The container SHALL bind its HTTP server to the port given by the `PORT`
environment variable (default `8080`) on all interfaces, so managed platforms
that inject `$PORT` can route traffic to it.

#### Scenario: Binds to the injected port

- **WHEN** the container is started with `PORT` set by the platform
- **THEN** the server listens on that port on `0.0.0.0`

### Requirement: Stateless, scale-to-zero operation

The service SHALL hold no per-instance persistent state, so it can run zero or
more interchangeable instances and scale to zero when idle without data loss.

#### Scenario: Cold start after idle

- **WHEN** no instance is running and a request arrives
- **THEN** a new instance starts and serves the request (accepting a cold-start
  latency), with no dependence on prior in-memory state
