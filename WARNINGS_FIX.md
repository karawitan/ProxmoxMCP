# RuntimeWarning Fix for ProxmoxMCP

## Problème identifié

Le projet ProxmoxMCP utilise la bibliothèque `proxmoxer` pour interagir avec l'API Proxmox. Cette bibliothèque contient une ligne problématique dans son code :

```python
# Dans proxmoxer/backends/https.py
requests.packages.urllib3.disable_warnings()
```

Cette ligne désactive **TOUS** les warnings urllib3, pas seulement ceux liés aux certificats SSL. Cela peut masquer des `RuntimeWarning` importants et d'autres avertissements qui pourraient indiquer des bugs ou des problèmes dans l'application.

## Solution implémentée

### 1. Module `utils/warnings_fix.py`

Ce module fournit une approche ciblée pour gérer les warnings :

- **`setup_warning_filters()`** : Configure les filtres de warnings pour toute l'application
- **`fix_proxmoxer_warnings()`** : Corrige spécifiquement le problème de proxmoxer
- **`configure_ssl_warnings()`** : Permet un contrôle fin des warnings SSL

### 2. Intégration dans le serveur

Le fix est appliqué automatiquement lors de l'importation du serveur principal dans `server.py` :

```python
import warnings
# Configure warnings before importing other modules
warnings.filterwarnings('default')  # Enable all warnings by default

from .utils.warnings_fix import setup_warning_filters
# Set up warning filters early
setup_warning_filters()
```

### 3. Comportement après correction

- ✅ **RuntimeWarnings** : Visibles pour le débogage
- ✅ **DeprecationWarnings** : Visibles pour la maintenance du code
- ✅ **Autres warnings importants** : Visibles selon leur importance
- ❌ **SSL warnings (InsecureRequestWarning)** : Supprimés pour réduire le bruit

## Tests

### Tests unitaires

```bash
# Exécuter les tests du fix
python -m pytest tests/test_warnings_fix.py -v
```

### Démonstration

```bash
# Démonstration comparative avant/après
python demo_warnings_fix.py

# Démonstration d'usage réaliste
python realistic_demo.py
```

## Usage

Le fix est appliqué automatiquement lors de l'importation du module `proxmox_mcp.server`. Aucune action supplémentaire n'est requise.

Pour l'utiliser dans d'autres parties du code :

```python
from proxmox_mcp.utils.warnings_fix import setup_warning_filters

# Appliquer le fix
setup_warning_filters()
```

## Configuration avancée

Pour personnaliser le comportement des warnings :

```python
from proxmox_mcp.utils.warnings_fix import configure_ssl_warnings

# Désactiver complètement la suppression des warnings SSL
configure_ssl_warnings(suppress_ssl_warnings=False)

# Ou réactiver la suppression
configure_ssl_warnings(suppress_ssl_warnings=True)
```

## Impact

- **Avant le fix** : Les RuntimeWarnings peuvent être masqués par la suppression globale de proxmoxer
- **Après le fix** : Tous les warnings importants sont visibles, seuls les warnings SSL bruyants sont supprimés
- **Compatibilité** : Aucun changement d'API, le fix est transparent pour l'utilisateur final

## Fichiers modifiés

1. `src/proxmox_mcp/utils/warnings_fix.py` - Nouveau module avec le fix
2. `src/proxmox_mcp/server.py` - Application du fix lors de l'initialisation
3. `src/proxmox_mcp/core/proxmox.py` - Import du fix après proxmoxer
4. `tests/test_warnings_fix.py` - Tests unitaires
5. `demo_warnings_fix.py` - Démonstration du problème et de la solution
6. `realistic_demo.py` - Démonstration d'usage réaliste

Ce fix garantit que les RuntimeWarnings et autres warnings importants restent visibles pour faciliter le débogage et la maintenance, tout en éliminant le bruit des warnings SSL non pertinents.
