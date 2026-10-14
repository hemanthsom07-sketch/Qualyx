# Qualyx Architecture

## 1. Purpose

Qualyx aims to provide a workflow for recording user journeys, executing browser tests, collecting evidence, analyzing failures, and improving test maintainability.

The architecture separates the user interface, API and persistence, browser execution, recording, and intelligence responsibilities so that each component can be developed and tested independently.

## 2. High-Level Architecture

```text
                 Developer / Tester
                         |
                         v
                 React Dashboard
                         |
                         v
                   FastAPI Backend
                    /     |      \
                   v      v       v
              PostgreSQL  Test   Intelligence
                         Engine   Component
                           |
                           v
                      Playwright
                           |
                           v
                    Target Web App

Browser Interactions ---> Recorder
                              |
                              v
                    Recorded Journey Data
```

This diagram represents the intended logical responsibilities. Exact runtime connections and the degree of integration must be verified against the current implementation.

## 3. Components

### Dashboard

**Location:** `dashboard/`

The dashboard is the user-facing web application. It provides the interface through which users are intended to interact with projects, test definitions, executions, and diagnostic results.

**Technology:** React, TypeScript, and Vite.

The dashboard communicates with the backend through the API contracts implemented by the project.

### Backend

**Location:** `backend/`

The backend is responsible for API endpoints, application logic, data access, and coordination of supported workflows.

**Technology:** Python, FastAPI, SQLAlchemy, and Alembic.

PostgreSQL provides persistent storage. Alembic migrations manage database schema changes.

The backend should validate requests, handle failures explicitly, and keep configuration separate from source code.

### Execution Engine

**Location:** `execution-engine/`

The execution engine runs browser-based tests using Playwright and the Node.js ecosystem.

Its responsibilities include executing test scenarios and reporting results and diagnostic information to the surrounding platform.

Execution behavior, browser availability, and integration with the backend must be verified through tests.

### Recorder

**Location:** `recorder/`

The recorder is intended to capture user interactions in a browser and represent them as structured journey data that can support repeatable testing.

Captured actions need appropriate validation and conversion before they are used to create or execute tests.

### Intelligence

**Location:** `intelligence/`

The intelligence component is intended to support analysis of test failures and diagnostic evidence.

Its broader goals include helping identify likely failure causes and informing test-maintenance decisions. The exact capabilities available today should be determined from the implemented modules and tests.

### Demo Application

**Location:** `demo-app/`

The demo application provides a controlled target for developing and demonstrating browser-based testing workflows.

It can be used to reproduce expected behavior and failures without relying exclusively on an external application.

## 4. Data and Execution Flow

The intended workflow is:

1. A user selects or configures a project through the dashboard.
2. User interactions may be captured by the recorder.
3. Journey data is validated and represented as a test definition.
4. The backend coordinates the supported execution workflow.
5. The execution engine runs the test against a target application.
6. Results and available evidence are returned to the platform.
7. Diagnostic logic evaluates the failure information when applicable.
8. Any proposed test repair or application-code change is reviewed and verified before acceptance.

Not every step is necessarily integrated or automated yet. Treat this as the target workflow until end-to-end tests establish otherwise.

## 5. Persistence and Migrations

PostgreSQL is the intended relational database. SQLAlchemy handles database access, while Alembic manages schema migrations.

The initial schema baseline covers the core project, test-definition, and execution-run entities. The complete data model may evolve as additional workflows are implemented.

Schema changes should be represented by reviewed migrations. Developers should avoid relying on automatic schema creation for normal development or deployment.

## 6. Failure Diagnosis and Repair

Qualyx distinguishes between two different activities:

- **Test maintenance:** Updating a test when a selector or interaction becomes outdated.
- **Application repair:** Investigating and changing application source code when the application itself is defective.

A failed test is evidence of a problem, but it is not by itself proof of an application bug. Diagnosis should consider execution output, assertions, browser errors, and other available evidence.

Any proposed repair should be validated against the relevant tests before being accepted. Automated application-code changes require additional safeguards and should not be assumed to be available simply because diagnostic functionality exists.

## 7. Quality and Security Principles

- Validate API inputs and recorded browser actions.
- Avoid storing secrets in source control.
- Use least-privilege access to databases and services.
- Preserve useful execution diagnostics without exposing sensitive data.
- Test components independently and verify integration separately.
- Make failure analysis explainable and distinguish observed evidence from inferred causes.
- Require explicit verification before treating a proposed repair as successful.

## 8. Verification Boundaries

A component's tests can establish behavior within that component's test scope. They do not automatically establish that the dashboard, backend, recorder, execution engine, database, and intelligence component work together in a deployed environment.

End-to-end integration and deployment checks remain necessary before making production-readiness claims.
