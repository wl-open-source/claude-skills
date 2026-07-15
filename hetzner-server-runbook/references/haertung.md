# Härtung: Ubuntu 24.04 Basis-Absicherung

Alle Befehle zunächst als `root@<SERVER_IP>` per ssh.

## 1. System aktualisieren

```bash
# NEEDRESTART_MODE=a + noninteractive: sonst blockiert Ubuntu 24.04 an einem
# needrestart-/Service-Neustart-Dialog und der Befehl hängt.
DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a apt-get update
DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a apt-get -y upgrade
```

## 2. Deploy-User anlegen (sudo, ohne Passwort-Login)

```bash
adduser --disabled-password --gecos "" deploy
usermod -aG sudo deploy
echo "deploy ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/deploy
chmod 440 /etc/sudoers.d/deploy
mkdir -p /home/deploy/.ssh
cp /root/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh && chmod 600 /home/deploy/.ssh/authorized_keys
```

**Prüfen, bevor Root-Login abgeschaltet wird** (neue Terminal-Session!):

```bash
ssh deploy@<SERVER_IP> "sudo whoami"   # → root
```

## 3. SSH härten — ⚠️ erst nach erfolgreichem deploy-Login!

```bash
cat > /etc/ssh/sshd_config.d/99-hardening.conf <<'EOF'
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
X11Forwarding no
EOF
sshd -t && systemctl restart ssh
```

## 4. Firewall (ufw)

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
ufw status verbose
```

## 5. fail2ban + automatische Security-Updates

```bash
apt-get install -y fail2ban unattended-upgrades
cat > /etc/fail2ban/jail.local <<'EOF'
[sshd]
enabled = true
backend = systemd
EOF
systemctl enable --now fail2ban
systemctl restart fail2ban
dpkg-reconfigure -f noninteractive unattended-upgrades
```

## 6. Verifikation

```bash
ssh root@<SERVER_IP> "echo geht-noch" # Erwartung: Permission denied
ssh deploy@<SERVER_IP> "sudo ufw status | head -3 && sudo fail2ban-client status sshd | head -5"
```
