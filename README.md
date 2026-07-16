# Comparateur de prix

Outil de comparaison de prix utilisant Selenium pour interroger plusieurs sites marchands, avec une interface graphique Tkinter.

## Fonctionnalités

- Recherche simultanée sur plusieurs sites (Pcmaroc, Electroplanet, Pcmarrakech)
- Filtrage par mots-clés et par plage de prix
- Interface graphique avec suivi en temps réel de la recherche
- Export des résultats en CSV
- Utilisation possible en ligne de commande

## Prérequis

- Python 3
- Google Chrome installé

## Installation

```
pip install selenium beautifulsoup4
```

## Utilisation

Interface graphique :

```
python main_gui.py
```

Ligne de commande :

```
python selenuim_search.py "pc portable hp" --min-price 3000 --max-price 8000
```

## Structure

```
comparateur_prix/
├── main_gui.py
└── selenuim_search.py
```
