# Organització del treball amb Kanban

## Entorn virtual i dependències

Des de l’arrel del repositori, crea un entorn virtual (exemple amb carpeta `.venv`):

```bash
python -m venv .venv
```

Activa’l segons el sistema:

* **Windows (PowerShell):** `.venv\Scripts\Activate.ps1`

Instal·la les dependències del projecte:

```bash
pip install -r requirements.txt
```

## Preparació de la base de dades (desenvolupament)

Amb l’entorn virtual activat, des de l’arrel del projecte:

```bash
python manage.py prepare_dev_database
```

Aquesta comanda aplica les **migracions**, crea els **grups de tots els rols** definits a l’aplicació i assegura el **superusuari** `admin` / `admin`. No crea encara usuaris de prova ni dades d’analítica (això va després del catàleg).

Flux recomanat, en ordre:

1. `python manage.py prepare_dev_database` — migracions + rols + `admin` / `admin`
2. `python manage.py sync_catalog` — catàleg des de les APIs (cal tenir l’API aixecada)
3. `python manage.py populate_db` — usuaris de prova (un per cada rol; **un gestor per plataforma** amb nom `gestor_<id_plataforma>`) i **100 visualitzacions** aleatòries

Contrasenyes de prova després de `populate_db` (excepte `admin`):

| Usuari | Contrasenya | Rol |
|--------|----------------|-----|
| `consumidor` | `consumidor` | Consumidor de contingut |
| `admin_tecnic` | `devpass` | Administrador tècnic |
| `director_general` | `devpass` | Director general |
| `gestor_<id>` | `devpass` | Gestor de plataformes (una compta per plataforma) |

Els comandaments individuals `create_roles` i `create_admin_user` encara es poden cridar per separat si cal.

Per sincronitzar el catàleg:

```bash
python manage.py sync_catalog
```
>Obviament s'ha de tenir l'API aixecada per poder sincronitzar.

Per omplir usuaris de prova i visualitzacions (després del sync):

```bash
python manage.py populate_db
```

---

El projecte es gestiona mitjançant un **tauler Kanban** a GitHub Projects per visualitzar l’estat de les tasques.

## Columnes del tauler

```
Backlog → Ready → In Progress → Review → Done
```

### Backlog

Tasques pendents encara no planificades.

### Ready

Tasques preparades per començar.

### In Progress

Tasques en desenvolupament.

### Review

Tasques acabades pendents de revisió.

### Done

Tasques completades.

---

## Assignació de tasques

* Només les persones assignades a un issue/tasca poden treballar en aquella tasca.

**Important:**

* **No es pot treballar en una tasca assignada a una altra persona** sense avisar prèviament al **Scrum Master** (@MiquelBaron).
* Qualsevol canvi s’ha de comunicar abans per evitar conflictes.

---

## Treball amb branques

* Cada tasca es desenvolupa en una **branca pròpia**.
* No es treballa directament sobre `main`.

### Exemple:

```
feature/login
bugfix/error-registre
```

* Cada desenvolupador treballa sempre a la seva branca.
* Els canvis es pugen mitjançant **Pull Requests**.

---

## Flux de treball

1. Assignació de la tasca a una persona
2. Revisar l’issue i entendre clarament tots els passos definits
3. Si no estan clars els passos, **no es pot començar a programar**
4. En cas de dubtes, consultar amb el **Scrum Master**
5. Crear una **branca** per la tasca
6. Moure la tasca a **In Progress**
7. Desenvolupar seguint els passos indicats a l’issue
8. Crear un **Pull Request**
9. Moure a **Review**
10. Un cop validat → **Done**

---

## Objectiu

* Evitar conflictes entre desenvolupadors
* Tenir responsabilitats clares
* Assegurar que totes les tasques es desenvolupen seguint els requisits definits
* Mantenir el projecte organitzat i controlat
