# Podman Systemd Integration

## Quadlet (Recommended, Podman 4.4+)

Quadlet lets you define containers as systemd unit files. Place `.container` files in:

- User: `~/.config/containers/systemd/`
- System: `/etc/containers/systemd/`

### Container Unit

```ini
# ~/.config/containers/systemd/myapp.container
[Unit]
Description=My Application
After=network-online.target

[Container]
Image=docker.io/myorg/myapp:latest
PublishPort=8080:8080
Environment=NODE_ENV=production
Volume=myapp-data:/data:Z
Network=myapp.network
AutoUpdate=registry

[Service]
Restart=on-failure
RestartSec=10
TimeoutStartSec=60

[Install]
WantedBy=default.target
```

### Network Unit

```ini
# ~/.config/containers/systemd/myapp.network
[Network]
Subnet=10.89.0.0/24
Gateway=10.89.0.1
```

### Volume Unit

```ini
# ~/.config/containers/systemd/myapp-data.volume
[Volume]
Label=app=myapp
```

### Pod Unit

```ini
# ~/.config/containers/systemd/myapp.pod
[Pod]
PodName=myapp
PublishPort=8080:8080
PublishPort=5432:5432
```

### Activate Quadlet Units

```bash
# Reload systemd to discover new units
systemctl --user daemon-reload

# Start and enable
systemctl --user start myapp.service
systemctl --user enable myapp.service

# Check status
systemctl --user status myapp.service

# View logs
journalctl --user -u myapp.service -f
```

## Legacy: podman generate systemd

For Podman < 4.4 or one-off conversions:

```bash
# Generate systemd unit from running container
podman generate systemd --name myapp --new --files

# Install for current user
mkdir -p ~/.config/systemd/user
cp container-myapp.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now container-myapp.service
```

### Generated Unit Example

```ini
# container-myapp.service
[Unit]
Description=Podman container-myapp.service
Wants=network-online.target
After=network-online.target

[Service]
Environment=PODMAN_SYSTEMD_UNIT=%n
Restart=on-failure
TimeoutStopSec=70
ExecStartPre=/bin/rm -f %t/%n.ctr-id
ExecStart=/usr/bin/podman run \
    --cidfile=%t/%n.ctr-id \
    --cgroups=no-conmon \
    --rm \
    --sdnotify=conmon \
    -d \
    --replace \
    --name myapp \
    -p 8080:8080 \
    myimage:latest
ExecStop=/usr/bin/podman stop --ignore --cidfile=%t/%n.ctr-id
ExecStopPost=/usr/bin/podman rm -f --ignore --cidfile=%t/%n.ctr-id
Type=notify
NotifyAccess=all

[Install]
WantedBy=default.target
```

## Auto-Updates

```bash
# Enable auto-update timer
systemctl --user enable --now podman-auto-update.timer

# Check for updates manually
podman auto-update

# Dry run
podman auto-update --dry-run
```

Requires `AutoUpdate=registry` in the Quadlet `.container` file or the `io.containers.autoupdate=registry` label.

## Enabling Lingering (User Services Without Login)

```bash
# Allow user services to run after logout
loginctl enable-linger $USER

# Verify
loginctl show-user $USER | grep Linger
```

## Full Stack Example

```ini
# ~/.config/containers/systemd/webapp.network
[Network]
Subnet=10.89.1.0/24

# ~/.config/containers/systemd/db.container
[Unit]
Description=PostgreSQL Database

[Container]
Image=docker.io/library/postgres:16
Environment=POSTGRES_PASSWORD=secret
Environment=POSTGRES_DB=myapp
Volume=db-data:/var/lib/postgresql/data:Z
Network=webapp.network
HealthCmd=pg_isready -U postgres
HealthInterval=10s

[Service]
Restart=always

[Install]
WantedBy=default.target

# ~/.config/containers/systemd/api.container
[Unit]
Description=API Server
After=db.service

[Container]
Image=docker.io/myorg/api:latest
Environment=DATABASE_URL=postgresql://postgres:secret@systemd-db:5432/myapp
PublishPort=8080:8080
Network=webapp.network

[Service]
Restart=on-failure

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user start db.service api.service
```
