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

En desenvolupament el flux es divideix en **tres comandaments** que cal executar **en aquest ordre**. El primer prepara només l’esquema i els rols; el segon omple el catàleg des de les APIs externes; el tercer crea usuaris de prova i dades d’analítica que depenen del catàleg.

### 1. `prepare_dev_database`

```bash
python manage.py prepare_dev_database
```

**Què fa:**

- Aplica totes les **migracions** de Django.
- Crea els **grups de rol** de l’aplicació (Consumidor de contingut, Administrador tècnic, Director general, Gestor de plataformes).
- Assegura un **superusuari** per accedir a l’admin de Django: usuari `admin`, contrasenya `admin`.

**Què no fa:** no descarrega pel·lícules ni sèries, no crea usuaris de prova amb rols ni visualitzacions. És el pas mínim per tenir una base buida però consistent.

---

### 2. `sync_catalog`

```bash
python manage.py sync_catalog
```

**Què fa:**

- Llegeix les dades de les **APIs de les plataformes** configurades al projecte (vegeu `ss/catalog_api.py`: claus `platform1`, `platform2`, etc.).
- Omple o actualitza el catàleg local: plataformes, gèneres, directors, valoracions d’edat, pel·lícules, sèries i relacions amb plataformes.

**Requisit:** les APIs han d’estar **aixecades i accessibles** (per defecte `localhost` amb els ports definits al codi). Si no responen, el sync pot acabar sense errors greus però amb pocs o cap contingut.

---

### 3. `populate_db`

```bash
python manage.py populate_db
```

**Què fa:**

- Crea **un usuari de prova per cada tipus de rol** (excepte el superusuari, que ja és `admin`).
- Per al rol **Gestor de plataformes**, crea **un usuari per cada plataforma** que hi hagi a la base després del `sync_catalog`, amb nom d’usuari `gestor_<id>` (on `<id>` és la clau primària de la fila `Platform` a la base de dades).
- Genera **100 visualitzacions de prova** aleatòries (usuari, contingut, plataforma i data), útils per provar cerques, informes PDF de gestor, etc.

Cal haver executat abans **`sync_catalog`** perquè hi hagi plataformes i continguts; si no, els gestors no es poden crear per plataforma i les visualitzacions no es generen correctament.

Cada vegada que executes `populate_db` s’afegeixen **100 visualitzacions més** (no es buiden les anteriors). Els usuaris de prova es creen de forma idempotent (`get_or_create`): si ja existeixen, es reutilitzen i només s’actualitzen rols o plataformes si cal.

---

### Usuaris i contrasenyes de prova

Després de `populate_db` pots iniciar sessió al web amb aquests comptes (el superusuari `admin` / `admin` ja existeix des del pas 1):

| Usuari | Contrasenya | Rol / ús |
|--------|---------------|----------|
| `admin` | `admin` | Superusuari (Django admin); no té necessàriament els grups de rol de l’app |
| `consumidor` | `consumidor` | Consumidor de contingut (perfil consumidor, preferències, etc.) |
| `admin_tecnic` | `devpass` | Administrador tècnic |
| `director_general` | `devpass` | Director general |
| `gestor_<id>` | `devpass` | Gestor de plataformes: cada un està vinculat a **una** plataforma concreta (exportació PDF d’informe només per aquella plataforma) |

Exemple: si després del sync tens tres plataformes amb `id` 1, 2 i 3, tindràs `gestor_1`, `gestor_2` i `gestor_3`, tots amb contrasenya `devpass`.

---

### Comandaments auxiliars

Encara pots cridar per separat `create_roles` i `create_admin_user` si només vols actualitzar rols o l’usuari admin sense repetir tot el flux.

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
