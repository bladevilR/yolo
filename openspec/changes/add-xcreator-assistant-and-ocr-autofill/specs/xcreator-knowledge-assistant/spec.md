## ADDED Requirements

### Requirement: Page-Embedded Assistant Entry
The system SHALL provide a configurable assistant entrypoint for XCreator runtime pages without changing existing page data APIs or business operation buttons.

#### Scenario: Floating assistant enabled for a page
- **WHEN** a user opens an XCreator page where the assistant feature flag is enabled
- **THEN** the page displays a floating assistant entry that can expand into an assistant panel without hiding existing grid controls

#### Scenario: Assistant disabled for a page
- **WHEN** a user opens an XCreator page where the assistant feature flag is disabled
- **THEN** the page does not load or display the assistant widget

#### Scenario: Fallback entry is configured
- **WHEN** floating injection is unavailable or disabled for a page
- **THEN** the system SHALL provide a menu, button, iframe, or open-window entry to the same assistant experience

### Requirement: Retrieval-Grounded Answers
The assistant SHALL answer through the configured knowledge-system adapter using only approved knowledge-base sources and SHALL include source references for supported answers.

#### Scenario: Supported answer found
- **WHEN** a user asks a question that matches content returned by the configured knowledge-system adapter
- **THEN** the assistant returns an answer with source references sufficient for the user to inspect the basis of the response

#### Scenario: No supported answer found
- **WHEN** a user asks a question that is not supported by content returned by the configured knowledge-system adapter
- **THEN** the assistant states that it cannot answer from the knowledge base and does not invent an answer

### Requirement: Knowledge-System Adapter Contract
The assistant backend SHALL expose a stable adapter contract for connecting to an existing knowledge-base system without requiring the XCreator page integration to know the vendor-specific API.

#### Scenario: Adapter endpoint configured
- **WHEN** a tenant/app/page has a configured knowledge-system adapter endpoint
- **THEN** assistant questions are sent through the adapter using the configured authentication and request schema

#### Scenario: Adapter endpoint not configured
- **WHEN** a tenant/app/page has no configured knowledge-system adapter endpoint
- **THEN** the assistant is hidden, disabled, or shown in a placeholder mode and does not attempt live Q&A

#### Scenario: Adapter returns an error
- **WHEN** the configured knowledge-system adapter times out or returns an error
- **THEN** the assistant shows a recoverable error and does not fabricate an answer

### Requirement: Permission-Scoped Retrieval
The assistant SHALL restrict retrieved knowledge and answers according to the user's tenant, application, role, page configuration, and permissions returned or enforced by the existing knowledge system.

#### Scenario: User lacks access to a source
- **WHEN** a user asks a question whose best matching source is outside the user's permissions
- **THEN** the assistant excludes that source from retrieval and does not reveal its content

#### Scenario: User has page-scoped knowledge access
- **WHEN** a user asks from an enabled XCreator page
- **THEN** the adapter request includes page and user scope so retrieval includes only permitted knowledge

### Requirement: Safe Page Context
The assistant SHALL accept limited page context to improve answers without logging or exposing sensitive tokens.

#### Scenario: Page context is sent
- **WHEN** the widget calls the assistant service from an XCreator page
- **THEN** the request includes safe context such as tenant, appCode, pageCode, pageId, page title, and selected feature configuration

#### Scenario: Token redaction
- **WHEN** assistant requests, responses, logs, or diagnostics are stored
- **THEN** user tokens, app tokens, session tokens, and raw authentication parameters are redacted

### Requirement: Conversation Audit And Feedback
The assistant SHALL record auditable interaction metadata and allow users to flag poor or unsafe answers.

#### Scenario: Answer is generated
- **WHEN** the assistant returns an answer
- **THEN** the system records timestamp, user/page context identifiers, knowledge source identifiers, retrieval confidence metadata, and answer status without storing sensitive tokens

#### Scenario: User flags an answer
- **WHEN** a user marks an answer as incorrect or unhelpful
- **THEN** the system stores the feedback for knowledge-base review without altering production business records

### Requirement: Knowledge Adapter Configuration
The system SHALL provide a controlled way to configure assistant enablement, adapter endpoint aliases, adapter credentials, source-scope hints, and page-level availability.

#### Scenario: Adapter alias configured
- **WHEN** an administrator configures a knowledge adapter alias for a page or role
- **THEN** eligible users can ask questions through that adapter from the assistant

#### Scenario: Adapter health check fails
- **WHEN** a configured knowledge adapter fails its health check
- **THEN** the system reports the adapter as unavailable and prevents production enablement for affected pages
