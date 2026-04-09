# test.py
from services import (
    get_movies, get_series, get_directors, get_genres, get_age_ratings,
    get_all_movies, get_all_series, get_all_directors, get_all_genres, get_all_age_ratings,
    PLATFORMS
)

def test_per_plataforma():
    recursos = {
        "Movies":      get_movies,
        "Series":      get_series,
        "Directors":   get_directors,
        "Genres":      get_genres,
        "Age Ratings": get_age_ratings,
    }
    for platform in PLATFORMS.keys():
        print(f"\n{'='*40}")
        print(f" PLATAFORMA: {platform}")
        print(f"{'='*40}")

        for nom, func in recursos.items():
            dades = func(platform)
            print(f"\n  [{nom}] → {len(dades)} resultats")
            if dades:
                print(f"  Primer: {dades[0]}")
            else:
                print(f"  (buit)")


def test_totes_les_bd():
    recursos = {
        "Movies":      get_all_movies,
        "Series":      get_all_series,
        "Directors":   get_all_directors,
        "Genres":      get_all_genres,
        "Age Ratings": get_all_age_ratings,
    }

    print(f"\n{'='*40}")
    print(f" TOTES LES BD COMBINADES")
    print(f"{'='*40}")

    for nom, func in recursos.items():
        dades = func()
        print(f"\n  [{nom}] → {len(dades)} resultats totals")
        if dades:
            print(f"  Primer: {dades[0]}")
        else:
            print(f"  (buit)")


if __name__ == "__main__":
    print("\n>>> TEST PER PLATAFORMA")
    test_per_plataforma()

    print("\n\n>>> TEST COMBINAT (3 BD)")
    test_totes_les_bd()