"""Templates d'e-mails transactionnels DIVARC (HTML compatible clients mail + version texte)."""
from __future__ import annotations


def otp_email_html(code: str) -> str:
    """E-mail HTML professionnel pour le code de connexion (tables + styles inline)."""
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>Ton code DIVARC</title>
</head>
<body style="margin:0;padding:0;background-color:#f2f0e9;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f2f0e9;padding:32px 16px;font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;background-color:#ffffff;border-radius:20px;overflow:hidden;box-shadow:0 10px 34px rgba(20,22,43,0.09);">
        <tr>
          <td style="background-image:linear-gradient(135deg,#4353F0,#2C39C7);background-color:#4353F0;padding:30px 32px;">
            <table role="presentation" cellpadding="0" cellspacing="0"><tr>
              <td width="46" style="width:46px;">
                <table role="presentation" cellpadding="0" cellspacing="0"><tr>
                  <td align="center" valign="middle" width="46" height="46" style="width:46px;height:46px;background-color:rgba(255,255,255,0.16);border-radius:13px;">
                    <span style="font-family:Georgia,'Times New Roman',serif;font-style:italic;font-size:27px;line-height:27px;color:#E2AA2B;font-weight:bold;">D</span>
                  </td>
                </tr></table>
              </td>
              <td style="padding-left:14px;">
                <div style="color:#ffffff;font-size:22px;font-weight:700;letter-spacing:0.5px;">DIVARC</div>
                <div style="color:rgba(255,255,255,0.72);font-size:12px;">La super-app europ&eacute;enne</div>
              </td>
            </tr></table>
          </td>
        </tr>
        <tr>
          <td style="padding:36px 32px 26px;">
            <h1 style="margin:0 0 10px;font-size:22px;color:#14162B;font-weight:700;">Ton code de connexion</h1>
            <p style="margin:0 0 26px;font-size:15px;line-height:1.55;color:#5b5f73;">Saisis ce code dans l&rsquo;application DIVARC pour te connecter en toute s&eacute;curit&eacute;.</p>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
              <td align="center" style="background-color:#f4f3fb;border:1px solid #e5e3f5;border-radius:14px;padding:24px 12px;">
                <div style="font-size:40px;font-weight:800;letter-spacing:12px;color:#2C39C7;font-family:'Courier New',Courier,monospace;padding-left:12px;">{code}</div>
              </td>
            </tr></table>
            <p style="margin:22px 0 0;font-size:13px;color:#8a8d9c;text-align:center;">Ce code expire dans <strong style="color:#5b5f73;">10&nbsp;minutes</strong>.</p>
          </td>
        </tr>
        <tr>
          <td style="padding:0 32px 32px;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
              <td style="background-color:#f2f0e9;border-radius:12px;padding:16px 18px;font-size:13px;line-height:1.55;color:#5b5f73;">
                &#128274;&nbsp; Si tu n&rsquo;es pas &agrave; l&rsquo;origine de cette demande, ignore simplement cet e-mail &mdash; ton compte reste prot&eacute;g&eacute;.
              </td>
            </tr></table>
          </td>
        </tr>
        <tr>
          <td style="padding:24px 32px;background-color:#fafaf7;border-top:1px solid #eeece4;text-align:center;">
            <div style="font-size:12px;color:#a0a3b0;line-height:1.7;">
              DIVARC &middot; Paiement, messagerie &amp; assistant IA<br>
              Conforme RGPD &middot; H&eacute;berg&eacute; dans l&rsquo;UE
            </div>
          </td>
        </tr>
      </table>
      <div style="max-width:480px;margin:16px auto 0;font-size:11px;color:#b5b8c2;text-align:center;font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
        Cet e-mail automatique ne peut pas recevoir de r&eacute;ponse.
      </div>
    </td></tr>
  </table>
</body>
</html>"""


def welcome_email_html(name: str, app_url: str) -> str:
    """E-mail HTML de bienvenue à la création du compte (tables + styles inline)."""
    first = (name or "").split(" ")[0] or "et bienvenue"
    features = [
        ("&#128179;", "Paiements &amp; wallet", "Envoie de l&rsquo;argent en un instant, cr&eacute;e des enveloppes cadeaux."),
        ("&#128172;", "Messagerie &amp; appels", "Discute, partage photos et vid&eacute;os, appelle en audio ou vid&eacute;o."),
        ("&#10024;", "Assistant IA DIVA", "Ton assistant personnel pour agir dans l&rsquo;app."),
        ("&#128269;", "D&eacute;couvrir &amp; social", "Retrouve tes amis, la marketplace et le fil vid&eacute;o."),
    ]
    rows = ""
    for emoji, title, desc in features:
        rows += f"""<tr>
          <td width="34" valign="top" style="width:34px;font-size:20px;line-height:24px;">{emoji}</td>
          <td style="padding:0 0 14px 6px;">
            <div style="font-size:15px;color:#14162B;font-weight:600;">{title}</div>
            <div style="font-size:13px;line-height:1.5;color:#5b5f73;">{desc}</div>
          </td>
        </tr>"""
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>Bienvenue sur DIVARC</title>
</head>
<body style="margin:0;padding:0;background-color:#f2f0e9;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f2f0e9;padding:32px 16px;font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;background-color:#ffffff;border-radius:20px;overflow:hidden;box-shadow:0 10px 34px rgba(20,22,43,0.09);">
        <tr>
          <td style="background-image:linear-gradient(135deg,#4353F0,#2C39C7);background-color:#4353F0;padding:30px 32px;">
            <table role="presentation" cellpadding="0" cellspacing="0"><tr>
              <td width="46" style="width:46px;">
                <table role="presentation" cellpadding="0" cellspacing="0"><tr>
                  <td align="center" valign="middle" width="46" height="46" style="width:46px;height:46px;background-color:rgba(255,255,255,0.16);border-radius:13px;">
                    <span style="font-family:Georgia,'Times New Roman',serif;font-style:italic;font-size:27px;line-height:27px;color:#E2AA2B;font-weight:bold;">D</span>
                  </td>
                </tr></table>
              </td>
              <td style="padding-left:14px;">
                <div style="color:#ffffff;font-size:22px;font-weight:700;letter-spacing:0.5px;">DIVARC</div>
                <div style="color:rgba(255,255,255,0.72);font-size:12px;">La super-app europ&eacute;enne</div>
              </td>
            </tr></table>
          </td>
        </tr>
        <tr>
          <td style="padding:36px 32px 8px;">
            <h1 style="margin:0 0 10px;font-size:23px;color:#14162B;font-weight:700;">Bienvenue {first}&nbsp;&#127881;</h1>
            <p style="margin:0 0 24px;font-size:15px;line-height:1.55;color:#5b5f73;">Ton compte DIVARC est cr&eacute;&eacute;. Tout est r&eacute;uni dans une seule app, con&ccedil;ue pour la confiance et conforme au RGPD.</p>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}</table>
          </td>
        </tr>
        <tr>
          <td align="center" style="padding:14px 32px 34px;">
            <table role="presentation" cellpadding="0" cellspacing="0"><tr>
              <td align="center" style="background-image:linear-gradient(135deg,#4353F0,#2C39C7);background-color:#2C39C7;border-radius:14px;">
                <a href="{app_url}" style="display:inline-block;padding:14px 34px;font-size:15px;font-weight:700;color:#ffffff;text-decoration:none;">Ouvrir DIVARC</a>
              </td>
            </tr></table>
          </td>
        </tr>
        <tr>
          <td style="padding:24px 32px;background-color:#fafaf7;border-top:1px solid #eeece4;text-align:center;">
            <div style="font-size:12px;color:#a0a3b0;line-height:1.7;">
              DIVARC &middot; Paiement, messagerie &amp; assistant IA<br>
              Conforme RGPD &middot; H&eacute;berg&eacute; dans l&rsquo;UE
            </div>
          </td>
        </tr>
      </table>
      <div style="max-width:480px;margin:16px auto 0;font-size:11px;color:#b5b8c2;text-align:center;font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
        Cet e-mail automatique ne peut pas recevoir de r&eacute;ponse.
      </div>
    </td></tr>
  </table>
</body>
</html>"""


def welcome_email_text(name: str, app_url: str) -> str:
    first = (name or "").split(" ")[0] or ""
    return (
        f"Bienvenue {first} sur DIVARC !\n\n"
        "Ton compte est créé. DIVARC réunit dans une seule app :\n"
        "- Paiements & wallet (envois instantanés, enveloppes cadeaux)\n"
        "- Messagerie, photos/vidéos et appels audio/vidéo\n"
        "- Assistant IA DIVA\n"
        "- Découvrir, marketplace et fil social\n\n"
        f"Ouvrir DIVARC : {app_url}\n\n"
        "DIVARC · Conforme RGPD · Hébergé dans l'UE\n"
        "Cet e-mail automatique ne peut pas recevoir de réponse."
    )


def otp_email_text(code: str) -> str:
    """Version texte brut (repli pour les clients sans HTML)."""
    return (
        "DIVARC — Ton code de connexion\n\n"
        f"Ton code : {code}\n\n"
        "Saisis ce code dans l'application pour te connecter. Il expire dans 10 minutes.\n\n"
        "Si tu n'es pas à l'origine de cette demande, ignore cet e-mail.\n\n"
        "DIVARC · Conforme RGPD · Hébergé dans l'UE"
    )
