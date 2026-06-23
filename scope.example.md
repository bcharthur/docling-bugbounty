# Scope — exemple (à adapter au programme YesWeHack réel)

> Remplace ce contenu par le scope exact du programme. L'agent s'appuie
> dessus pour ne proposer que des tests autorisés.

## Dans le périmètre (autorisé)
- *.example.com (applications web)
- api.example.com (API REST)
- Application mobile Android/iOS « ExampleApp »

## Hors périmètre (interdit)
- Tout domaine non listé ci-dessus
- Déni de service (DoS/DDoS), tests de charge
- Ingénierie sociale, phishing des employés
- Attaques physiques
- Tests sur les comptes d'autres utilisateurs

## Types de vulnérabilités acceptées
- Injection (SQLi, NoSQLi, command injection)
- XSS, SSRF, IDOR, contournement d'authentification/autorisation
- Désérialisation, RCE

## Règles
- Pas d'exfiltration de données réelles d'utilisateurs.
- Utiliser un compte de test dédié.
- Signaler immédiatement toute donnée sensible découverte.
