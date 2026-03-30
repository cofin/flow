# Security Auditor Checklist

OWASP-informed categories for security review. For each category, assess whether the code has a finding. If it does, assign a severity and explain the attack vector and fix. If the code is secure in a category, a brief acknowledgment is sufficient.

1. **Injection** (SQL, command, template, XSS)
   Is user input sanitized before use in database queries, shell commands, template rendering, or HTML output? Are parameterized queries used for database access? Is output encoded for the appropriate context (HTML, JavaScript, URL)?

2. **Authentication**
   Are credentials stored securely (hashed with bcrypt/argon2/scrypt, properly salted)? Are sessions managed correctly (secure/httpOnly cookies, regenerated on login, invalidated on logout)? Is MFA available or enforced where the risk warrants it? Are brute-force protections in place?

3. **Authorization**
   Are access controls enforced at every entry point, not just the UI? Can a user escalate privileges by manipulating IDs or parameters (IDOR)? Are object-level permissions checked — not just "is the user authenticated" but "does this user have access to this specific resource"?

4. **Data exposure**
   Are secrets hardcoded in source code or configuration committed to version control? Are sensitive fields (passwords, tokens, PII) appearing in logs or error messages? Is PII handled according to applicable policy (minimized, encrypted at rest, not over-retained)?

5. **Input validation**
   Is all external input validated at system boundaries — before processing, not just before storage? Are type, length, and format constraints enforced? Are file uploads validated for type and content, not just extension?

6. **Configuration**
   Are default credentials changed? Are debug endpoints and admin interfaces disabled in production? Are CORS policies restrictive (not `*` for credentialed requests)? Are security headers present (CSP, HSTS, X-Frame-Options)?

7. **Dependencies**
   Are known-vulnerable versions of dependencies in use? Are dependency versions pinned (not using floating ranges in production)? Are there dependencies that are no longer maintained?

8. **Cryptography**
   Are strong, current algorithms used (AES-256, SHA-256+, RSA-2048+, no MD5/SHA-1 for security purposes)? Are keys rotated? Is TLS enforced for all external communication? Are random values for security purposes generated with a cryptographically secure source?
