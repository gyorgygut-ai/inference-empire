# Apple Shortcuts

Shortcuts collection.

**Process**:

- **Plan**: turn requirements into small Shortcut steps
- **(P)review**: proposed exact touches to implement the Shortcut
- **Build**: if approved, build the shortcut as per agreed plan

**Acceptance**:
  
- **Unsigned Artifact**: created at `{projectRoot}/<name>_unsigned.shortcut`
- **Signed Artifact**: created at `{projectRoot}/<name>_signed.shortcut`
- **Production-ready**: file must be ready for drag-n-drop into Shortcuts app

**Commands**:

- `shortcuts sign -i <name>_unsigned.shortcut -o <name>.shortcut`

---

## TODO: Planned Shortcuts

### Reusable, atomic

**Request OpenAI-compatible**:

- **1. Shortcut Input**: Request
- **2. Build a POST request**:
  - Base URL: text url, required shortcut input
  - API Key: text, required shortcut input
  - Model: text, required shortcut input
- **3. Show built request**
- **4. Send the POST request**
  - Assume OpenAI API contract
- **5. Shortcut Output**: response message / error

### Reusable, coupled

**Use Groq Free**:

- **1. Shortcut Input**: text
- **2. Build the payload**:
  - Base URL: groq api url, hardcoded
  - API Key: groq api key, get from Keychain
  - Message: shortcut input
- **3. Show built request**:
- **4. Run `Request OpenAI-compatible`**:
  - Input: the built request
- **5. Shortcut Output**:
  - On fail: show error message + status
  - On success: show response message

**Use Gemini Free**:

- **1. Shortcut Input**: text
- **2. Build the payload**:
  - Base URL: gemini api url, hardcoded
  - API Key: gemini api key, get from Keychain
  - Message: shortcut input
- **3. Show built request**:
- **4. Run `Request OpenAI-compatible`**:
  - Input: the built request
- **5. Shortcut Output**:
  - On fail: show error message + status
  - On success: show response message

### Compose Reusables

**Use Model Fallback**:

- **1. Shortcut Input**: text
- **2. IF `Use Model` Shortcut available**:
  - Run `Use Model` shortcut, pass shortcut input
- **2.1 ELSE**:
  - Run `Use Groq Free`, pass shortcut input
    - On success: response message to var `responseMessage`
    - On fail: Run `Use Gemini Free`, pass shortcut input
      - On success: response message to variable
      - On fail: error message to var `responseMessage`
- **3. Show variable `responseMessage`**
