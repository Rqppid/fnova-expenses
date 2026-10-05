"""Notifications: Windows toast (if someone is at the PC) plus an email to self."""
from __future__ import annotations

import subprocess

TOAST_PS = r"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$t = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$n = $t.GetElementsByTagName('text')
$n.Item(0).AppendChild($t.CreateTextNode($env:FN_TITLE)) | Out-Null
$n.Item(1).AppendChild($t.CreateTextNode($env:FN_BODY)) | Out-Null
$app = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app).Show([Windows.UI.Notifications.ToastNotification]::new($t))
"""


def toast(title: str, body: str) -> bool:
    import os
    env = dict(os.environ, FN_TITLE=title[:120], FN_BODY=body[:240])
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", TOAST_PS],
                           env=env, capture_output=True, timeout=30)
        return r.returncode == 0
    except Exception:
        return False


def notify(title: str, body: str, gmail_svc=None) -> list[str]:
    """Returns the channels that worked."""
    done = []
    if toast(title, body.splitlines()[0] if body else ""):
        done.append("toast")
    if gmail_svc is not None:
        try:
            from .gmail import send_self
            send_self(gmail_svc, f"[Fone Nova expenses] {title}", body)
            done.append("email")
        except Exception:
            pass
    return done
