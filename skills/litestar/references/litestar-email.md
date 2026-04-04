# Litestar Email Plugin

`litestar-email` provides a pluggable email sending abstraction for Litestar with multiple backend drivers and first-class DI support.

## Installation

```bash
pip install litestar-email
# Optional extras for specific backends:
pip install litestar-email[resend]
pip install litestar-email[sendgrid]
pip install litestar-email[mailgun]
```

## Basic Setup

```python
from litestar import Litestar
from litestar_email import EmailPlugin, EmailConfig, SMTPConfig

app = Litestar(plugins=[EmailPlugin(config=EmailConfig(
    backend=SMTPConfig(
        host="smtp.example.com",
        port=587,
        use_tls=True,
        username="user@example.com",
        password="secret",
    ),
    from_email="noreply@example.com",
    from_name="My App",
))])
```

## EmailConfig

| Option | Type | Description |
|--------|------|-------------|
| `backend` | `BackendConfig` | One of: `SMTPConfig`, `ResendConfig`, `SendGridConfig`, `MailgunConfig`, `InMemoryConfig` |
| `from_email` | `str` | Default sender address |
| `from_name` | `str \| None` | Optional display name for sender |

## Backend Configurations

### SMTPConfig

```python
from litestar_email import SMTPConfig

SMTPConfig(
    host="smtp.gmail.com",
    port=587,
    use_tls=True,           # STARTTLS
    use_ssl=False,          # Implicit SSL (port 465)
    username="you@gmail.com",
    password="app-password",
    timeout=10,             # seconds
)
```

### ResendConfig

```python
from litestar_email import ResendConfig

ResendConfig(api_key="re_xxxxxxxxxx")
```

### SendGridConfig

```python
from litestar_email import SendGridConfig

SendGridConfig(api_key="SG.xxxxxxxxxx")
```

### MailgunConfig

```python
from litestar_email import MailgunConfig

MailgunConfig(
    api_key="key-xxxxxxxxxx",
    domain="mg.example.com",
    region="us",  # or "eu"
)
```

### InMemoryConfig (testing)

```python
from litestar_email import InMemoryConfig

InMemoryConfig()
# Stores sent messages in memory; inspect via email_service.outbox
```

## Dependency Injection

`EmailPlugin.on_app_init` registers `EmailService` in Litestar's DI container automatically.

```python
from litestar import post
from litestar_email import EmailService, EmailMessage

@post("/send-notification")
async def send_notification(
    email_service: EmailService,
    data: NotificationRequest,
) -> dict:
    await email_service.send_message(EmailMessage(
        to=[data.recipient],
        subject="Notification",
        body="You have a new notification.",
        html_body="<p>You have a new notification.</p>",
    ))
    return {"sent": True}
```

## EmailMessage

```python
from litestar_email import EmailMessage

EmailMessage(
    to=["recipient@example.com"],          # required
    subject="Hello",                        # required
    body="Plain text body",                 # optional
    html_body="<p>HTML body</p>",           # optional
    cc=["cc@example.com"],
    bcc=["bcc@example.com"],
    reply_to="reply@example.com",
    from_email="override@example.com",      # overrides EmailConfig default
    from_name="Override Name",
    headers={"X-Custom": "value"},
    attachments=[("/path/to/file.pdf", "application/pdf")],
)
```

## EmailMultiAlternatives

For sending a message with both plain text and HTML parts explicitly:

```python
from litestar_email import EmailMultiAlternatives

msg = EmailMultiAlternatives(
    to=["user@example.com"],
    subject="Welcome",
    body="Welcome to our platform.",
)
msg.attach_alternative("<p>Welcome to our platform.</p>", "text/html")
await email_service.send_message(msg)
```

## EmailService Methods

| Method | Description |
|--------|-------------|
| `send_message(msg)` | Send a single `EmailMessage` |
| `send_messages(msgs)` | Send a list of messages (batch) |

Both methods are `async`.

### Async Context Manager

`EmailService` can be used as an async context manager for connection pooling (SMTP):

```python
async with email_service as svc:
    await svc.send_message(msg1)
    await svc.send_message(msg2)
```

## Testing with InMemoryBackend

```python
from litestar_email import InMemoryConfig, EmailConfig, EmailPlugin

def create_test_app():
    return Litestar(plugins=[EmailPlugin(config=EmailConfig(
        backend=InMemoryConfig(),
        from_email="test@example.com",
    ))])

async def test_sends_email(test_client):
    response = test_client.post("/send-notification", json={"recipient": "user@example.com"})
    assert response.status_code == 201

    email_service = test_client.app.dependencies["email_service"]
    assert len(email_service.outbox) == 1
    assert email_service.outbox[0].subject == "Notification"
```

## Standalone Usage (without Litestar DI)

```python
from litestar_email import EmailConfig, SMTPConfig

config = EmailConfig(
    backend=SMTPConfig(host="smtp.example.com", port=587, use_tls=True),
    from_email="noreply@example.com",
)

async def main():
    async with config.provide_service() as email_service:
        await email_service.send_message(EmailMessage(
            to=["user@example.com"],
            subject="Hello",
            body="World",
        ))
```

## Notes

- All backends support async send; `SMTPConfig` uses `aiosmtplib` internally.
- Use `InMemoryConfig` in all test environments — avoids real network calls and provides an `outbox` for assertions.
- `from_email` at the `EmailMessage` level overrides the `EmailConfig` default for that message only.
- For bulk transactional email at scale, prefer `ResendConfig` or `SendGridConfig` over direct SMTP.
