# PassVault 🔐

Gestionnaire de mots de passe de bureau, simple et sécurisé, écrit en Python avec **PySide6** (Qt) pour l'interface et **PyNaCl** (bindings de *libsodium*) pour la cryptographie.

Ce projet est le portage Python d'une application originellement écrite en C++/Qt : la logique et le format de fichier restent équivalents, tout en s'appuyant sur les mêmes primitives cryptographiques (libsodium) côté C.

## ✨ Fonctionnalités

- 🔒 Coffre chiffré localement, protégé par un mot de passe maître
- 🧂 Dérivation de clé **Argon2id** (résistante aux attaques GPU/ASIC)
- 🔑 Chiffrement authentifié **XChaCha20-Poly1305** (AEAD, nonce 24 octets)
- 🧹 Effacement sécurisé des secrets en mémoire (`SecureBytes`, verrouillage mémoire `mlock`/`VirtualLock`)
- 🎲 Générateur de mots de passe cryptographiquement sûr (`secrets`)
- 🖥️ Interface graphique Qt (PySide6) : ajout, modification, suppression et copie d'entrées
- 📋 Copie du mot de passe dans le presse-papiers

## 🏗️ Architecture

| Fichier | Rôle |
|---|---|
| `main.py` | Point d'entrée de l'application |
| `main_window.py` | Fenêtre principale (table des entrées, actions) |
| `unlock_dialog.py` | Boîte de dialogue de création/déverrouillage du coffre |
| `entry_dialog.py` | Boîte de dialogue d'ajout/modification d'une entrée |
| `vault.py` | Logique du coffre : lecture/écriture du fichier chiffré, entrées |
| `crypto_manager.py` | Chiffrement, déchiffrement, dérivation de clé (libsodium via PyNaCl) |
| `secure_bytes.py` | Buffer mémoire verrouillé et effacé pour les données sensibles |
| `password_generator.py` | Génération de mots de passe aléatoires |

### Format du fichier `.vault`

```
[ 16 octets de sel Argon2id, en clair ]
[ nonce (24 octets) || ciphertext || tag d'authentification ]
```

Le sel n'est pas secret : il est nécessaire pour re-dériver la clé à chaque déverrouillage.

## 🚀 Installation

### Prérequis

- Python 3.10+
- [libsodium](https://libsodium.gitbook.io/doc/) (généralement installé automatiquement avec PyNaCl)

### Étapes

```bash
git clone https://github.com/<votre-utilisateur>/passvault.git
cd passvault

python -m venv venv
source venv/bin/activate      # Windows : venv\Scripts\activate

pip install -r requirements.txt
```

`requirements.txt` :

```
PySide6
PyNaCl
```

## ▶️ Utilisation

```bash
python main.py
```

Au premier lancement, le coffre est créé dans `~/.passvault/vault.dat` après le choix d'un mot de passe maître. Aux lancements suivants, ce mot de passe est demandé pour déverrouiller le coffre existant.

## 🔐 Détails de sécurité

- **Dérivation de clé** : Argon2id via `crypto_pwhash` (niveau `MODERATE` : ~64 Mo de RAM, ~0.7 s CPU)
- **Chiffrement** : XChaCha20-Poly1305 IETF (AEAD), sans données additionnelles authentifiées (AAD)
- **Mémoire** : les secrets sensibles peuvent être stockés dans des `SecureBytes`, verrouillés en mémoire (`mlock`/`VirtualLock`) et explicitement mis à zéro (`wipe()`) après usage
- ⚠️ Limite connue : contrairement à un `QByteArray` en C++, les objets `bytes`/`str` Python sont immuables et peuvent être dupliqués silencieusement par l'interpréteur (interning, optimisations). L'effacement mémoire reste donc *best-effort* pour tout ce qui transite hors de `SecureBytes`.

## 📦 Dépendances principales

- [PySide6](https://pypi.org/project/PySide6/) — bindings Qt6 pour Python
- [PyNaCl](https://pypi.org/project/PyNaCl/) — bindings Python de libsodium

## 📄 Licence

À définir (par exemple MIT) — ajoutez un fichier `LICENSE` selon vos préférences.

## ⚠️ Avertissement

Ce projet est fourni à titre éducatif/personnel. Avant toute utilisation pour stocker des mots de passe réels et sensibles, il est recommandé de faire auditer le code par un tiers compétent en sécurité.
